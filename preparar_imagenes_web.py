"""Prepara lotes completos sin modificar productos.json ni los JPG originales."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from PIL import Image, ImageOps


def preparar(origen, sitio, codigos, ambientes=("03", "04"), base_url=None):
    catalogo = {str(p["codigo"]): p for p in json.loads((sitio / "productos.json").read_text(encoding="utf-8-sig"))}
    destino = sitio / "media" / "catalogo"
    manifiesto = sitio / "galerias.json"
    datos = json.loads(manifiesto.read_text(encoding="utf-8")) if manifiesto.exists() else {"version": 1, "baseUrl": "", "productos": {}}
    if base_url is not None:
        if base_url and not base_url.startswith("https://"):
            raise ValueError("La URL pública debe empezar con https://")
        datos["baseUrl"] = base_url.rstrip("/")
    trabajos = []
    # Validar el lote entero antes de publicar cualquier cambio en el manifiesto.
    for codigo in codigos:
        if codigo not in catalogo or not codigo.isdigit():
            raise ValueError(f"Código desconocido: {codigo}")
        orientacion = catalogo[codigo]["orientacion"].lower()
        if orientacion not in ("horizontal", "vertical"):
            raise ValueError(f"Orientación no compatible: {codigo}: {orientacion}")
        letra = "H" if orientacion == "horizontal" else "V"
        nombres = [f"{codigo}_PRODUCTO_{letra}_01", *[f"{codigo}_AMBIENTE_{letra}_{a}" for a in ambientes], f"{codigo}_PRODUCTO_D_01"]
        for nombre, etiqueta in zip(nombres, ("Obra", "Ambiente 1", "Ambiente 2", "Detalle")):
            archivo = origen / (nombre + ".jpg")
            if not archivo.is_file():
                raise ValueError(f"Falta {archivo.name}; no se actualizó el lote.")
            with Image.open(archivo) as im:
                im.verify()
            trabajos.append((codigo, nombre, etiqueta, archivo))
    destino.mkdir(parents=True, exist_ok=True)
    nuevos = {}
    total = original = 0
    for codigo, nombre, etiqueta, archivo in trabajos:
        original += archivo.stat().st_size
        with Image.open(archivo) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            variantes = {}
            for ancho, calidad in ((160, 76), (640, 80), (1254, 84)):
                copia = im.copy()
                copia.thumbnail((ancho, ancho), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                copia.save(buffer, "WEBP", quality=calidad, method=6)
                contenido = buffer.getvalue()
                version = hashlib.sha256(contenido).hexdigest()[:12]
                ruta = f"media/catalogo/{nombre}-{version}-{ancho}.webp"
                salida = sitio / ruta
                if not salida.exists():
                    salida.write_bytes(contenido)
                variantes[str(ancho)] = {"ruta": ruta, "ancho": copia.width, "bytes": len(contenido)}
                total += len(contenido)
        nuevos.setdefault(codigo, []).append({"etiqueta": etiqueta, "variantes": variantes})
    datos["productos"].update(nuevos)
    temporal = manifiesto.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporal, manifiesto)
    print(f"Listo: {len(nuevos)} obras, {len(trabajos)} vistas. JPG originales: {original:,} bytes. WebP (todos los tamaños): {total:,} bytes.")
    return datos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origen", type=Path, required=True)
    parser.add_argument("--sitio", type=Path, default=Path(__file__).resolve().parent)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--codigos", nargs="+")
    grupo.add_argument("--todos", action="store_true", help="Solo códigos con un mockup PRODUCTO_H/V_01 en origen")
    parser.add_argument("--ambientes", nargs=2, default=["03", "04"], choices=["01", "02", "03", "04"])
    parser.add_argument("--base-url", default=None, help="Origen HTTPS de R2/CDN; omitir conserva el alojamiento actual")
    args = parser.parse_args()
    codigos = args.codigos or sorted({p.name.split("_")[0] for p in args.origen.glob("*_PRODUCTO_[HV]_01.jpg")})
    if not codigos:
        parser.error("No se encontraron obras para preparar")
    try:
        preparar(args.origen, args.sitio, codigos, args.ambientes, args.base_url)
    except (ValueError, OSError) as error:
        parser.exit(1, f"ERROR: {error}\n")
