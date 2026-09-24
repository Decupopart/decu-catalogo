# -*- coding: utf-8 -*-
"""Convierte el catálogo CSV en productos.json para la web de Decu."""

import argparse
import csv
import json
import os
import re
import tempfile


CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PREDETERMINADO = os.path.join(CARPETA_BASE, "catalogo_procesado.csv")
JSON_PREDETERMINADO = os.path.join(CARPETA_BASE, "productos.json")
IMAGENES_PREDETERMINADAS = os.path.join(CARPETA_BASE, "Imagenes")
RUTA_WEB_IMAGENES = "Imagenes"

# Columnas mínimas para identificar y mostrar cada producto. El resto es opcional.
COLUMNAS_REQUERIDAS = {"CODIGO", "NOMBRE", "CATEGORIA", "FORMATO"}

CAMPOS_JSON = {
    "SUBCATEGORIA": "subcategoria",
    "TONALIDAD": "tonalidad",
    "AMBIENTE": "ambiente",
    "ESTILO": "estilo",
    "EMOCION": "emocion",
    "IMPACTO_VISUAL": "impacto_visual",
    "TECNICA_VISUAL": "tecnica_visual",
}


def argumentos():
    parser = argparse.ArgumentParser(description="Genera productos.json desde el catálogo CSV.")
    parser.add_argument("--csv", default=CSV_PREDETERMINADO, help="Ruta del catálogo CSV.")
    parser.add_argument(
        "--imagenes",
        default=IMAGENES_PREDETERMINADAS,
        help="Carpeta que contiene los mockups.",
    )
    parser.add_argument(
        "--salida",
        default=JSON_PREDETERMINADO,
        help="Ruta del productos.json que se generará.",
    )
    return parser.parse_args()


def texto(valor):
    return "" if valor is None else str(valor).strip()


def clave_columna(valor):
    clave = texto(valor).upper()
    clave = re.sub(r"[^A-Z0-9ÁÉÍÓÚÜÑ]+", "_", clave)
    return clave.strip("_")


def slug_campo(valor):
    clave = clave_columna(valor).lower()
    return clave.translate(str.maketrans("áéíóúüñ", "aeiouun"))


def leer_catalogo(ruta_csv):
    with open(ruta_csv, encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo, delimiter=";")
        if not lector.fieldnames:
            raise ValueError("El CSV no contiene encabezados.")

        encabezados = [clave_columna(nombre) for nombre in lector.fieldnames]
        if len(encabezados) != len(set(encabezados)):
            raise ValueError("El CSV contiene encabezados duplicados.")

        faltantes = sorted(COLUMNAS_REQUERIDAS - set(encabezados))
        if faltantes:
            raise ValueError(
                "Faltan columnas necesarias en el CSV: " + ", ".join(faltantes)
            )

        filas = []
        for numero_fila, fila_original in enumerate(lector, start=2):
            fila = {
                clave_columna(nombre): texto(valor)
                for nombre, valor in fila_original.items()
                if nombre is not None
            }
            filas.append((numero_fila, fila))

    return encabezados, filas


def mapear_imagenes(carpeta_imagenes):
    """Escanea la carpeta y arma {codigo: nombre_de_archivo_real}."""
    mapa = {}
    duplicados = {}
    if not os.path.isdir(carpeta_imagenes):
        return mapa, duplicados

    for nombre_archivo in sorted(os.listdir(carpeta_imagenes)):
        if not nombre_archivo.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        codigo = nombre_archivo.split("-", 1)[0].strip()
        if not codigo.isdigit():
            continue
        if codigo in mapa:
            duplicados.setdefault(codigo, [mapa[codigo]]).append(nombre_archivo)
            continue
        mapa[codigo] = nombre_archivo
    return mapa, duplicados


def normalizar_categoria(valor):
    return texto(valor).title()


TONALIDAD_CANONICA = {
    "calido": "Cálido", "cálido": "Cálido", "frio": "Frío", "frío": "Frío",
    "blanco y negro": "Blanco y Negro", "dorado": "Dorado", "madera": "Madera",
    "metalico": "Metálico", "metálico": "Metálico", "natural": "Natural",
    "neutro": "Neutro", "oscuro": "Oscuro", "pastel": "Pastel",
    "tierra": "Tierra", "vibrante": "Vibrante",
}


def normalizar_tonalidad(valor):
    original = texto(valor)
    return TONALIDAD_CANONICA.get(original.lower(), original.title())


COLOR_CANONICO = {
    "marron": "marron", "marrón": "marron", "ocre": "ocre", "beige": "beige",
    "naranja": "naranja", "azul": "azul", "amarillo": "amarillo",
    "magenta": "magenta", "violeta": "violeta", "verde": "verde", "rojo": "rojo",
    "blanco": "blanco", "negro": "negro", "gris": "gris", "dorado": "dorado",
    "plateado": "plateado", "celeste": "celeste", "turquesa": "turquesa",
    "rosa": "rosa", "sepia": "sepia",
}


def normalizar_color(valor):
    clave = texto(valor).lower()
    return COLOR_CANONICO.get(clave, clave)


FORMATO_A_ORIENTACION = {
    "horizontal": "horizontal", "vertical": "vertical",
    "triptico": "triptico", "tríptico": "triptico",
}


def normalizar_orientacion(valor):
    clave = texto(valor).lower()
    return FORMATO_A_ORIENTACION.get(clave, clave)


def guardar_json_atomico(productos, ruta_salida):
    carpeta_salida = os.path.dirname(os.path.abspath(ruta_salida))
    os.makedirs(carpeta_salida, exist_ok=True)
    descriptor, ruta_temporal = tempfile.mkstemp(
        prefix="productos_", suffix=".json", dir=carpeta_salida
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(productos, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        os.replace(ruta_temporal, ruta_salida)
    except Exception:
        try:
            os.unlink(ruta_temporal)
        except OSError:
            pass
        raise


def convertir(ruta_csv, carpeta_imagenes, ruta_salida):
    encabezados, filas = leer_catalogo(ruta_csv)
    mapa_imagenes, imagenes_duplicadas = mapear_imagenes(carpeta_imagenes)

    productos = []
    sin_imagen = []
    filas_omitidas = []
    codigos_vistos = set()
    codigos_duplicados = set()

    columnas_conocidas = {
        "CODIGO", "NOMBRE", "CATEGORIA", "FORMATO", "COLORES",
        "MAS_VENDIDO", "ESTADO", *CAMPOS_JSON.keys(),
    }

    for numero_fila, fila in filas:
        codigo = texto(fila.get("CODIGO"))
        nombre = texto(fila.get("NOMBRE"))
        categoria = normalizar_categoria(fila.get("CATEGORIA"))
        formato = texto(fila.get("FORMATO"))

        if not codigo or not nombre or not categoria or not formato:
            filas_omitidas.append(numero_fila)
            continue

        if codigo in codigos_vistos:
            codigos_duplicados.add(codigo)
        codigos_vistos.add(codigo)

        colores = [
            normalizar_color(color)
            for color in texto(fila.get("COLORES")).split(",")
            if texto(color)
        ]
        nombre_imagen = mapa_imagenes.get(codigo)
        if not nombre_imagen:
            sin_imagen.append(codigo)

        producto = {
            "codigo": codigo,
            "nombre": nombre,
            "categoria": categoria,
            "subcategoria": texto(fila.get("SUBCATEGORIA")),
            "tonalidad": normalizar_tonalidad(fila.get("TONALIDAD")),
            "colores": colores,
            "orientacion": normalizar_orientacion(formato),
            "ambiente": texto(fila.get("AMBIENTE")),
            "estilo": texto(fila.get("ESTILO")),
            "emocion": texto(fila.get("EMOCION")),
            "impacto_visual": texto(fila.get("IMPACTO_VISUAL")),
            "tecnica_visual": texto(fila.get("TECNICA_VISUAL")),
            "imagen": f"{RUTA_WEB_IMAGENES}/{nombre_imagen}" if nombre_imagen else None,
            "mas_vendido": texto(fila.get("MAS_VENDIDO")).upper() == "SI",
        }

        # Las columnas futuras viajan al JSON sin modificar el esquema principal.
        atributos_adicionales = {
            slug_campo(campo): texto(fila.get(campo))
            for campo in encabezados
            if campo not in columnas_conocidas and texto(fila.get(campo))
        }
        if atributos_adicionales:
            producto["atributos"] = atributos_adicionales

        productos.append(producto)

    guardar_json_atomico(productos, ruta_salida)

    print(f"OK: {len(productos)} productos convertidos -> {ruta_salida}")
    print(f"  Columnas detectadas: {', '.join(encabezados)}")
    print(f"  Imágenes encontradas: {len(productos) - len(sin_imagen)}")
    print(f"  Categorías distintas: {len({p['categoria'] for p in productos})}")
    if sin_imagen:
        print(f"  AVISO: {len(sin_imagen)} productos todavía no tienen imagen.")
    if filas_omitidas:
        print("  AVISO: filas omitidas: " + ", ".join(map(str, filas_omitidas)))
    if codigos_duplicados:
        print("  AVISO: códigos duplicados: " + ", ".join(sorted(codigos_duplicados)))
    if imagenes_duplicadas:
        print(
            "  AVISO: más de una imagen para estos códigos: "
            + ", ".join(sorted(imagenes_duplicadas))
        )

    return productos


if __name__ == "__main__":
    args = argumentos()
    convertir(args.csv, args.imagenes, args.salida)
