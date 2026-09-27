# -*- coding: utf-8 -*-
"""Genera lienzos 3D (GLB) para el catálogo web de Decu.

El catálogo actual guarda una composición cuadrada: obra, nombre y referencia.
Este programa recorta la obra, la aplica a un bastidor 3D con continuidad visual
en los laterales y crea ``modelos-3d/modelos.json`` para la interfaz web.

Ejemplos:
    python generar_modelos_3d.py --codigos 3446 3449
    python generar_modelos_3d.py --todos
    python generar_modelos_3d.py --codigos 3446 --ancho-cm 90 --alto-cm 54
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import struct
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageEnhance, ImageOps
import qrcode


BASE = Path(__file__).resolve().parent
PRODUCTOS_PREDETERMINADOS = BASE / "productos.json"
SALIDA_PREDETERMINADA = BASE / "modelos-3d"
CSV_PREDETERMINADO = Path(
    r"C:\1. COPIA DE SEGURIDAD PC 2018\DECU 2025\00. SISTEMAS\04_Base de datos\catalogo_procesado.csv"
)
ORIGINALES_PREDETERMINADOS = Path(
    r"C:\1. COPIA DE SEGURIDAD PC 2018\DECU 2025\02. FABRICA DE MODELOS\01. IMAGENES\IMAGENES CODIFICADAS (PRUEBA)"
)
EXPORTACION_PREDETERMINADA = Path(
    r"C:\1. COPIA DE SEGURIDAD PC 2018\DECU 2025\02. FABRICA DE MODELOS\02. MOCK UP 3D"
)


@dataclass(frozen=True)
class Medidas:
    ancho_cm: float
    alto_cm: float
    profundidad_cm: float = 3.5


MEDIDAS_POR_ORIENTACION = {
    "horizontal": Medidas(90, 54),
    "vertical": Medidas(60, 100),
    "triptico": Medidas(120, 80),
    "tríptico": Medidas(120, 80),
}


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera modelos GLB con escala real para el visor 3D/AR de Decu."
    )
    parser.add_argument("--productos", type=Path, default=PRODUCTOS_PREDETERMINADOS)
    parser.add_argument("--csv", type=Path, default=CSV_PREDETERMINADO)
    parser.add_argument("--salida", type=Path, default=SALIDA_PREDETERMINADA)
    parser.add_argument(
        "--exportar",
        type=Path,
        default=EXPORTACION_PREDETERMINADA,
        help="Carpeta adicional donde se copiarán los modelos terminados.",
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--codigos", nargs="+", help="Códigos que se generarán.")
    grupo.add_argument("--todos", action="store_true", help="Genera todo el catálogo.")
    grupo.add_argument(
        "--disponibles",
        action="store_true",
        help="Genera únicamente los códigos encontrados en las carpetas de originales/reducidas.",
    )
    parser.add_argument("--ancho-cm", type=float, help="Sobrescribe el ancho para esta ejecución.")
    parser.add_argument("--alto-cm", type=float, help="Sobrescribe el alto para esta ejecución.")
    parser.add_argument("--profundidad-cm", type=float, default=3.5)
    parser.add_argument(
        "--originales",
        type=Path,
        default=ORIGINALES_PREDETERMINADOS,
        help="Carpeta con las obras originales, identificadas por código (ej.: 3446.jpg).",
    )
    parser.add_argument(
        "--reducidas",
        type=Path,
        help="Carpeta alternativa con versiones reducidas, también identificadas por código.",
    )
    parser.add_argument(
        "--recursivo",
        action="store_true",
        help="Incluye subcarpetas. Sin esta opción solo procesa archivos ubicados directamente en la carpeta elegida.",
    )
    parser.add_argument(
        "--sin-recorte",
        action="store_true",
        help="Usa la imagen completa. Útil si la entrada ya es la obra sin ficha blanca.",
    )
    parser.add_argument(
        "--max-textura",
        type=int,
        default=1600,
        help="Lado máximo de la textura exportada (predeterminado: 1600 px).",
    )
    parser.add_argument(
        "--base-url",
        default="https://decupopart.github.io/decu-catalogo/",
        help="URL pública del catálogo que se codificará en los QR.",
    )
    return parser.parse_args()


def cargar_productos(ruta_json: Path, ruta_csv: Path | None) -> list[dict]:
    """Combina productos.json con el CSV maestro, que prevalece en metadatos."""
    por_codigo: dict[str, dict] = {}
    if ruta_json.is_file():
        with ruta_json.open(encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, list):
            raise ValueError(f"{ruta_json} no contiene una lista de productos.")
        por_codigo.update(
            (str(producto.get("codigo", "")).strip(), dict(producto))
            for producto in datos
            if str(producto.get("codigo", "")).strip()
        )

    if ruta_csv and ruta_csv.is_file():
        with ruta_csv.open(encoding="utf-8-sig", newline="") as archivo:
            lector = csv.DictReader(archivo, delimiter=";")
            for fila in lector:
                codigo = str(fila.get("CODIGO", "")).strip()
                if not codigo:
                    continue
                producto = por_codigo.setdefault(codigo, {"codigo": codigo})
                producto.update({
                    "nombre": str(fila.get("NOMBRE", "")).strip() or codigo,
                    "categoria": str(fila.get("CATEGORIA", "")).strip(),
                    "subcategoria": str(fila.get("SUBCATEGORIA", "")).strip(),
                    "orientacion": str(fila.get("FORMATO", "")).strip().lower(),
                })

    if not por_codigo:
        raise FileNotFoundError(
            f"No se pudo leer el catálogo desde {ruta_json} ni desde {ruta_csv}."
        )
    return list(por_codigo.values())


def mapear_imagenes_por_codigo(
    carpeta: Path | None, recursivo: bool = False
) -> dict[str, Path]:
    """Mapea archivos de una carpeta a su código numérico inicial.

    Prefiere nombres exactos como ``3446.jpg`` sobre variantes descriptivas como
    ``3446.nombre-de-la-obra.jpg``. Las subcarpetas solo se incluyen con
    ``--recursivo``.
    """
    if carpeta is None:
        return {}
    carpeta = carpeta.expanduser().resolve()
    if not carpeta.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de imágenes: {carpeta}")
    extensiones = {".jpg", ".jpeg", ".png", ".webp"}
    mapa: dict[str, Path] = {}
    exactas: set[str] = set()
    candidatos = carpeta.rglob("*") if recursivo else carpeta.iterdir()
    for ruta in sorted(candidatos):
        if not ruta.is_file() or ruta.suffix.lower() not in extensiones:
            continue
        coincidencia = re.match(r"^(\d+)", ruta.stem)
        if not coincidencia:
            continue
        codigo = coincidencia.group(1)
        es_exacta = ruta.stem == codigo
        if codigo not in mapa or (es_exacta and codigo not in exactas):
            mapa[codigo] = ruta
        if es_exacta:
            exactas.add(codigo)
    return mapa


def caja_recorte(imagen: Image.Image, orientacion: str) -> tuple[int, int, int, int]:
    """Devuelve el área de la obra en la plantilla cuadrada actual de Decu.

    Los porcentajes reproducen los dos mockups vigentes (horizontal y vertical),
    pero se calculan sobre el tamaño real para no depender de 1095 × 1095 px.
    """
    ancho, alto = imagen.size
    orientacion = orientacion.lower().strip()
    if orientacion == "vertical":
        proporciones = (0.281, 0.049, 0.690, 0.760)
    elif orientacion in {"triptico", "tríptico"}:
        proporciones = (0.073, 0.112, 0.899, 0.610)
    else:
        proporciones = (0.073, 0.112, 0.899, 0.610)
    izquierda, arriba, derecha, abajo = proporciones
    return (
        round(ancho * izquierda),
        round(alto * arriba),
        round(ancho * derecha),
        round(alto * abajo),
    )


def preparar_textura(
    ruta_imagen: Path,
    orientacion: str,
    max_textura: int,
    sin_recorte: bool,
) -> Image.Image:
    with Image.open(ruta_imagen) as original:
        imagen = ImageOps.exif_transpose(original).convert("RGB")
    if not sin_recorte:
        imagen = imagen.crop(caja_recorte(imagen, orientacion))
    imagen.thumbnail((max_textura, max_textura), Image.Resampling.LANCZOS)
    # Una mejora mínima compensa la pérdida habitual de contraste del render PBR.
    return ImageEnhance.Contrast(imagen).enhance(1.02)


def empaquetar_floats(valores: Iterable[float]) -> bytes:
    valores = tuple(float(valor) for valor in valores)
    return struct.pack(f"<{len(valores)}f", *valores)


def empaquetar_enteros(valores: Iterable[int]) -> bytes:
    valores = tuple(int(valor) for valor in valores)
    return struct.pack(f"<{len(valores)}H", *valores)


class ConstructorBinario:
    def __init__(self) -> None:
        self.datos = bytearray()
        self.vistas: list[dict] = []

    def agregar(self, datos: bytes, objetivo: int | None = None) -> int:
        while len(self.datos) % 4:
            self.datos.append(0)
        vista = {"buffer": 0, "byteOffset": len(self.datos), "byteLength": len(datos)}
        if objetivo is not None:
            vista["target"] = objetivo
        indice = len(self.vistas)
        self.vistas.append(vista)
        self.datos.extend(datos)
        return indice


def _cara(
    posiciones: list[float],
    normales: list[float],
    uv: list[float],
    vertices: list[tuple[float, float, float]],
    normal: tuple[float, float, float],
    coordenadas_uv: list[tuple[float, float]],
) -> list[int]:
    inicio = len(posiciones) // 3
    for vertice, coordenada in zip(vertices, coordenadas_uv):
        posiciones.extend(vertice)
        normales.extend(normal)
        uv.extend(coordenada)
    return [inicio, inicio + 1, inicio + 2, inicio, inicio + 2, inicio + 3]


def crear_glb(textura: Image.Image, medidas: Medidas, destino: Path) -> None:
    """Crea un GLB autocontenido, sin Blender ni dependencias 3D externas."""
    ancho = medidas.ancho_cm / 100.0
    alto = medidas.alto_cm / 100.0
    profundidad = medidas.profundidad_cm / 100.0
    x, y, z = ancho / 2, alto / 2, profundidad / 2
    borde = min(0.035, max(0.012, profundidad / max(ancho, alto)))

    posiciones: list[float] = []
    normales: list[float] = []
    uv: list[float] = []
    indices_textura: list[int] = []
    indices_fondo: list[int] = []

    # Frente. Las UV mantienen la orientación natural de la imagen.
    indices_textura += _cara(
        posiciones, normales, uv,
        [(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)],
        (0, 0, 1),
        [(0, 1), (1, 1), (1, 0), (0, 0)],
    )
    # Laterales: cada cara toma una franja del borde de la obra para simular
    # la impresión continua del canvas alrededor del bastidor.
    indices_textura += _cara(
        posiciones, normales, uv,
        [(x, -y, z), (x, -y, -z), (x, y, -z), (x, y, z)],
        (1, 0, 0),
        [(1 - borde, 1), (1, 1), (1, 0), (1 - borde, 0)],
    )
    indices_textura += _cara(
        posiciones, normales, uv,
        [(-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z)],
        (-1, 0, 0),
        [(0, 1), (borde, 1), (borde, 0), (0, 0)],
    )
    indices_textura += _cara(
        posiciones, normales, uv,
        [(-x, y, z), (x, y, z), (x, y, -z), (-x, y, -z)],
        (0, 1, 0),
        [(0, 0), (1, 0), (1, borde), (0, borde)],
    )
    indices_textura += _cara(
        posiciones, normales, uv,
        [(-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z)],
        (0, -1, 0),
        [(0, 1 - borde), (1, 1 - borde), (1, 1), (0, 1)],
    )
    indices_fondo += _cara(
        posiciones, normales, uv,
        [(x, -y, -z), (-x, -y, -z), (-x, y, -z), (x, y, -z)],
        (0, 0, -1),
        [(0, 0), (1, 0), (1, 1), (0, 1)],
    )

    imagen_bytes = BytesIO()
    textura.save(imagen_bytes, format="JPEG", quality=91, optimize=True)

    binario = ConstructorBinario()
    vista_posiciones = binario.agregar(empaquetar_floats(posiciones), 34962)
    vista_normales = binario.agregar(empaquetar_floats(normales), 34962)
    vista_uv = binario.agregar(empaquetar_floats(uv), 34962)
    vista_indices_textura = binario.agregar(empaquetar_enteros(indices_textura), 34963)
    vista_indices_fondo = binario.agregar(empaquetar_enteros(indices_fondo), 34963)
    vista_imagen = binario.agregar(imagen_bytes.getvalue())

    cantidad_vertices = len(posiciones) // 3
    documento = {
        "asset": {"version": "2.0", "generator": "Decu generar_modelos_3d.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Lienzo Decu"}],
        "meshes": [{
            "name": "Lienzo canvas",
            "primitives": [
                {
                    "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                    "indices": 3,
                    "material": 0,
                },
                {
                    "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                    "indices": 4,
                    "material": 1,
                },
            ],
        }],
        "materials": [
            {
                "name": "Impresión canvas",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.84,
                },
                "doubleSided": False,
            },
            {
                "name": "Friselina negra del dorso",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.005, 0.005, 0.005, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.98,
                },
            },
        ],
        "textures": [{"sampler": 0, "source": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "images": [{"bufferView": vista_imagen, "mimeType": "image/jpeg"}],
        "accessors": [
            {
                "bufferView": vista_posiciones,
                "componentType": 5126,
                "count": cantidad_vertices,
                "type": "VEC3",
                "min": [-x, -y, -z],
                "max": [x, y, z],
            },
            {"bufferView": vista_normales, "componentType": 5126, "count": cantidad_vertices, "type": "VEC3"},
            {"bufferView": vista_uv, "componentType": 5126, "count": cantidad_vertices, "type": "VEC2"},
            {"bufferView": vista_indices_textura, "componentType": 5123, "count": len(indices_textura), "type": "SCALAR"},
            {"bufferView": vista_indices_fondo, "componentType": 5123, "count": len(indices_fondo), "type": "SCALAR"},
        ],
        "bufferViews": binario.vistas,
        "buffers": [{"byteLength": len(binario.datos)}],
    }

    json_bytes = json.dumps(documento, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    while len(binario.datos) % 4:
        binario.datos.append(0)
    longitud_total = 12 + 8 + len(json_bytes) + 8 + len(binario.datos)
    glb = bytearray(struct.pack("<4sII", b"glTF", 2, longitud_total))
    glb.extend(struct.pack("<I4s", len(json_bytes), b"JSON"))
    glb.extend(json_bytes)
    glb.extend(struct.pack("<I4s", len(binario.datos), b"BIN\x00"))
    glb.extend(binario.datos)
    destino.write_bytes(glb)


def medidas_producto(
    producto: dict,
    args: argparse.Namespace,
    aspecto_imagen: float | None = None,
    conservar_aspecto: bool = False,
) -> Medidas:
    orientacion = str(producto.get("orientacion", "horizontal")).lower()
    predeterminadas = MEDIDAS_POR_ORIENTACION.get(orientacion, MEDIDAS_POR_ORIENTACION["horizontal"])
    ancho = args.ancho_cm if args.ancho_cm else float(producto.get("ancho_cm") or predeterminadas.ancho_cm)
    alto = args.alto_cm if args.alto_cm else float(producto.get("alto_cm") or predeterminadas.alto_cm)
    tiene_medidas_explicitas = bool(
        args.ancho_cm or args.alto_cm or producto.get("ancho_cm") or producto.get("alto_cm")
    )
    if conservar_aspecto and aspecto_imagen and not tiene_medidas_explicitas:
        if orientacion == "vertical":
            ancho = alto * aspecto_imagen
        else:
            alto = ancho / aspecto_imagen
    return Medidas(ancho, alto, args.profundidad_cm)


def main() -> int:
    args = argumentos()
    productos = cargar_productos(args.productos, args.csv)
    por_codigo = {str(producto.get("codigo", "")): producto for producto in productos}
    originales = mapear_imagenes_por_codigo(args.originales, args.recursivo)
    reducidas = mapear_imagenes_por_codigo(args.reducidas, args.recursivo)
    if args.todos:
        codigos = sorted(por_codigo)
    elif args.disponibles:
        codigos = sorted((set(originales) | set(reducidas)) & set(por_codigo))
    else:
        codigos = [str(codigo) for codigo in args.codigos]
    args.salida.mkdir(parents=True, exist_ok=True)
    if args.exportar:
        args.exportar.mkdir(parents=True, exist_ok=True)
    indice = args.salida / "modelos.json"
    modelos: dict[str, dict] = {}
    if not args.todos and indice.is_file():
        try:
            existentes = json.loads(indice.read_text(encoding="utf-8"))
            if isinstance(existentes, dict):
                modelos.update(existentes)
        except (OSError, json.JSONDecodeError):
            pass
    errores: list[str] = []
    generados_ahora = 0

    for codigo in codigos:
        producto = por_codigo.get(codigo)
        if not producto:
            errores.append(f"{codigo}: no existe en productos.json")
            continue
        fuente = "mockup del catálogo"
        ruta_imagen = originales.get(codigo)
        if ruta_imagen:
            fuente = "original"
        else:
            ruta_imagen = reducidas.get(codigo)
            if ruta_imagen:
                fuente = "reducida"
        imagen_externa = ruta_imagen is not None
        if ruta_imagen is None:
            ruta_relativa = producto.get("imagen")
            ruta_imagen = args.productos.parent / str(ruta_relativa)
        if not ruta_imagen.is_file():
            errores.append(f"{codigo}: no se encontró {ruta_imagen}")
            continue
        orientacion = str(producto.get("orientacion") or "horizontal").lower()
        textura = preparar_textura(
            ruta_imagen,
            orientacion,
            args.max_textura,
            args.sin_recorte or imagen_externa,
        )
        aspecto = textura.width / textura.height
        medidas = medidas_producto(producto, args, aspecto, conservar_aspecto=imagen_externa)
        poster = args.salida / f"{codigo}-poster.jpg"
        modelo = args.salida / f"{codigo}.glb"
        qr = args.salida / f"{codigo}-qr.png"
        textura.save(poster, quality=91, optimize=True)
        crear_glb(textura, medidas, modelo)
        enlace_ar = f"{args.base_url.rstrip('/')}/?producto={codigo}&ar=1"
        qrcode.make(enlace_ar).save(qr)
        if args.exportar:
            for archivo_exportado in (poster, modelo, qr):
                shutil.copy2(archivo_exportado, args.exportar / archivo_exportado.name)
        modelos[codigo] = {
            "codigo": codigo,
            "nombre": producto.get("nombre", codigo),
            "modelo": f"modelos-3d/{modelo.name}",
            "poster": f"modelos-3d/{poster.name}",
            "qr": f"modelos-3d/{qr.name}",
            "enlace_ar": enlace_ar,
            "ancho_cm": medidas.ancho_cm,
            "alto_cm": medidas.alto_cm,
            "profundidad_cm": medidas.profundidad_cm,
            "fuente": fuente,
        }
        generados_ahora += 1
        print(
            f"OK {codigo}: {modelo.name} "
            f"({medidas.ancho_cm:g} × {medidas.alto_cm:g} cm, fuente: {fuente})"
        )

    indice.write_text(json.dumps(modelos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.exportar:
        modelos_exportados = {
            codigo: datos
            for codigo, datos in modelos.items()
            if (args.exportar / f"{codigo}.glb").is_file()
        }
        (args.exportar / indice.name).write_text(
            json.dumps(modelos_exportados, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"\nÍndice generado: {indice}")
    if args.exportar:
        print(f"Copia exportada: {args.exportar}")
    print(f"Modelos generados en esta ejecución: {generados_ahora}")
    if errores:
        print("\nAdvertencias:")
        for error in errores:
            print(f"- {error}")
    return 0 if modelos else 1


if __name__ == "__main__":
    raise SystemExit(main())
