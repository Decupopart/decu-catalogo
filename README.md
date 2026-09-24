# Catálogo Decu

Catálogo web filtrable de Decu para cuadros en lienzo sobre bastidor.

## Cómo actualizar el catálogo

1. Reemplazá `catalogo_procesado.csv` por la versión nueva.
2. Copiá los mockups nuevos dentro de `Imagenes`. El nombre puede contener todas las categorías; lo importante es que comience con el código y un guion, por ejemplo `520-...jpg`.
3. Desde esta carpeta ejecutá:

   ```powershell
   python generar_json.py
   ```

4. Revisá el resumen que muestra el programa. Informará productos sin imagen, códigos duplicados o filas incompletas.
5. Probá el sitio localmente:

   ```powershell
   python -m http.server 8000
   ```

   Luego abrí `http://localhost:8000`.
6. Subí `catalogo_procesado.csv`, `productos.json`, `Imagenes`, `generar_json.py` e `index.html` al repositorio.

GitHub Pages actualizará el sitio después de publicar los cambios.

## Campos compatibles

El sitio genera automáticamente filtros para:

- categoría;
- tonalidad;
- ambiente;
- estilo;
- emoción;
- impacto visual;
- técnica visual;
- orientación.

Si el JSON todavía es el anterior y no contiene los campos nuevos, esos filtros permanecen ocultos y el sitio continúa funcionando.

El generador solo exige `CODIGO`, `NOMBRE`, `CATEGORIA` y `FORMATO`. Las columnas adicionales del futuro se conservan dentro de `atributos` en `productos.json`.
