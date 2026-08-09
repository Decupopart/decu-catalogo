# -*- coding: utf-8 -*-
"""
generar_json.py
----------------
Convierte catalogo_procesado.csv al productos.json que usa la web del catálogo.

Uso:
    python generar_json.py

Requisitos: solo librerías estándar de Python (no necesita instalar nada).
"""

import csv
import json
import re

# ============================================================
# CONFIGURACIÓN — ajustar estas 3 líneas según tu proyecto
# ============================================================
import os

# Carpeta donde vive este script — así funciona sin importar desde dónde lo corras
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))

CSV_PATH = os.path.join(CARPETA_BASE, "catalogo_procesado.csv")
JSON_SALIDA = os.path.join(CARPETA_BASE, "productos.json")

# Carpeta con los mockups reales (deben estar acá cuando corras el script).
# Tus archivos ya tienen el código al principio del nombre, ej:
#   3064-Rugido_Silencioso-Animales-Felinos-Cálido-naranja__plateado-Vertical.jpg
# El script los detecta automáticamente, no hace falta renombrar nada.
CARPETA_IMAGENES = os.path.join(CARPETA_BASE, "Imagenes")
RUTA_WEB_IMAGENES = "Imagenes"  # tiene que coincidir EXACTO con el nombre de la carpeta subida al repo


def mapear_imagenes():
    """Escanea CARPETA_IMAGENES y arma {codigo: nombre_de_archivo_real}."""
    mapa = {}
    if not os.path.isdir(CARPETA_IMAGENES):
        return mapa
    for nombre_archivo in os.listdir(CARPETA_IMAGENES):
        if not nombre_archivo.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        codigo = nombre_archivo.split("-")[0].strip()
        if codigo.isdigit():
            mapa[codigo] = nombre_archivo
    return mapa


# ============================================================
# NORMALIZACIÓN — corrige inconsistencias de escritura del CSV
# ============================================================

def normalizar_categoria(valor):
    """'mujer' y 'Mujer' -> 'Mujer' (misma categoría, un solo filtro)."""
    return valor.strip().title()


TONALIDAD_CANONICA = {
    "calido": "Cálido",
    "cálido": "Cálido",
    "frio": "Frío",
    "frío": "Frío",
    "blanco y negro": "Blanco y Negro",
    "dorado": "Dorado",
    "madera": "Madera",
    "metalico": "Metálico",
    "metálico": "Metálico",
    "natural": "Natural",
    "neutro": "Neutro",
    "oscuro": "Oscuro",
    "pastel": "Pastel",
    "tierra": "Tierra",
    "vibrante": "Vibrante",
}

def normalizar_tonalidad(valor):
    clave = valor.strip().lower()
    return TONALIDAD_CANONICA.get(clave, valor.strip().title())


COLOR_CANONICO = {
    "marron": "marron", "marrón": "marron",
    "ocre": "ocre", "beige": "beige", "naranja": "naranja",
    "azul": "azul", "amarillo": "amarillo", "magenta": "magenta",
    "violeta": "violeta", "verde": "verde", "rojo": "rojo",
    "blanco": "blanco", "negro": "negro", "gris": "gris",
    "dorado": "dorado", "plateado": "plateado", "celeste": "celeste",
    "turquesa": "turquesa", "rosa": "rosa", "sepia": "sepia",
}

def normalizar_color(valor):
    clave = valor.strip().lower()
    return COLOR_CANONICO.get(clave, clave)


FORMATO_A_ORIENTACION = {
    "horizontal": "horizontal",
    "vertical": "vertical",
    "triptico": "triptico",
    "tríptico": "triptico",
}

def normalizar_orientacion(valor):
    clave = valor.strip().lower()
    return FORMATO_A_ORIENTACION.get(clave, clave)


# ============================================================
# CONVERSIÓN
# ============================================================

def convertir():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        lector = csv.DictReader(f, delimiter=";")
        filas = list(lector)

    mapa_imagenes = mapear_imagenes()

    productos = []
    cambios_categoria = set()
    cambios_tonalidad = set()
    sin_imagen = []

    for fila in filas:
        categoria_original = fila["CATEGORIA"].strip()
        tonalidad_original = fila["TONALIDAD"].strip()

        categoria = normalizar_categoria(categoria_original)
        tonalidad = normalizar_tonalidad(tonalidad_original)

        if categoria != categoria_original:
            cambios_categoria.add(f"{categoria_original} -> {categoria}")
        if tonalidad != tonalidad_original:
            cambios_tonalidad.add(f"{tonalidad_original} -> {tonalidad}")

        colores = [normalizar_color(c) for c in fila["COLORES"].split(",") if c.strip()]
        codigo = fila["CODIGO"].strip()

        nombre_imagen = mapa_imagenes.get(codigo)
        if nombre_imagen:
            imagen = f"{RUTA_WEB_IMAGENES}/{nombre_imagen}"
        else:
            imagen = None
            sin_imagen.append(codigo)

        productos.append({
            "codigo": codigo,
            "nombre": fila["NOMBRE"].strip(),
            "categoria": categoria,
            "subcategoria": fila["SUBCATEGORIA"].strip(),
            "tonalidad": tonalidad,
            "colores": colores,
            "orientacion": normalizar_orientacion(fila["FORMATO"]),
            "imagen": imagen,
        })

    with open(JSON_SALIDA, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)

    # ---- resumen para revisar ----
    print(f"✔ {len(productos)} productos convertidos -> {JSON_SALIDA}")
    print(f"  Imágenes encontradas en '{CARPETA_IMAGENES}/': {len(productos) - len(sin_imagen)}")
    if sin_imagen:
        print(f"  ⚠ Sin imagen todavía: {len(sin_imagen)} productos (se muestra ilustración de color como respaldo)")
    print(f"  Categorías distintas: {len(set(p['categoria'] for p in productos))}")
    print(f"  Tonalidades distintas: {len(set(p['tonalidad'] for p in productos))}")
    print(f"  Colores distintos: {len(set(c for p in productos for c in p['colores']))}")

    if cambios_categoria:
        print("\n  Categorías normalizadas (unificadas):")
        for c in sorted(cambios_categoria):
            print(f"    - {c}")

    if cambios_tonalidad:
        print("\n  Tonalidades normalizadas (unificadas):")
        for t in sorted(cambios_tonalidad):
            print(f"    - {t}")

    # colores/orientaciones que no matchearon ningún valor conocido
    colores_desconocidos = sorted({
        c for p in productos for c in p["colores"] if c not in COLOR_CANONICO.values()
    })
    if colores_desconocidos:
        print("\n  ⚠ Colores no reconocidos (revisar / agregar a COLOR_CANONICO):")
        for c in colores_desconocidos:
            print(f"    - {c}")


if __name__ == "__main__":
    convertir()
