# Imágenes del catálogo DECU

La obra 520 usa la nueva galería. Las otras conservan su imagen anterior hasta que se prepare su lote. El generador de productos.json puede seguir usándose: las galerías están separadas en galerias.json.

## Preparar un lote

Requiere Python y Pillow (`python -m pip install Pillow`). Ejecutar desde esta carpeta:

```powershell
python preparar_imagenes_web.py --origen "C:\1. COPIA DE SEGURIDAD PC 2018\DECU 2025\02. FABRICA DE MODELOS\02. MOCK UP CON PERSPECTIVA" --codigos 520 817
```

También se puede hacer doble clic en PREPARAR_LOTE_IMAGENES.cmd e ingresar códigos separados por espacios. Empezar con lotes pequeños para revisar el resultado antes de publicar.

Cada obra requiere cuatro JPG: CODIGO_PRODUCTO_H_01, CODIGO_AMBIENTE_H_03, CODIGO_AMBIENTE_H_04 y CODIGO_PRODUCTO_D_01. Para verticales se usa V en lugar de H (Detalle siempre D). La orientación se lee del catálogo, no se adivina. `--ambientes 01 02` permite elegir otra pareja. `--todos` procesa los códigos con un mockup de producto en la carpeta de origen. Si falta una vista, el manifiesto del lote no cambia.

## Publicar

1. Preparar el lote. Se conservan los JPG originales y las obras ya migradas.
2. Publicar los archivos nuevos de media/catalogo antes o junto con galerias.json. En GitHub Pages se pueden incluir en el mismo commit.
3. Revisar una ficha horizontal y una vertical. No borrar versiones antiguas mientras estén publicadas o en caché.

Se generan WebP de 160, 640 y hasta 1254 píxeles. Las miniaturas usan 160; el navegador elige la versión principal según pantalla y densidad. Solo la vista seleccionada descarga su imagen grande. El catálogo mantiene su carga progresiva. Los nombres incluyen una huella del contenido para evitar imágenes antiguas en caché.

## Cloudflare

La primera obra funciona con archivos del propio sitio. No necesita activar servicios adicionales. Para todo el catálogo, se recomienda un bucket R2 con dominio público propio y caché CDN. El Worker de los modelos 3D se conserva. Sus límites de archivos no son convenientes para sumar las 12 versiones por obra (2037 obras serían 24.444 imágenes).

Para cambiar el alojamiento: subir media/catalogo al nuevo almacenamiento conservando las rutas, verificar los archivos y luego establecer `baseUrl` en galerias.json, por ejemplo `https://imagenes.tudominio.com`. Nunca cambiar esa URL antes de que TODOS los archivos referenciados estén disponibles. El script acepta `--base-url` y conserva la URL en lotes posteriores si se omite ese argumento. No usar r2.dev para producción.

Configurar `Content-Type: image/webp` y `Cache-Control: public, max-age=31536000, immutable` en los WebP con huella. Si se necesita compartir las imágenes desde el navegador, habilitar CORS para el dominio del catálogo. galerias.json se mantiene en el sitio y se revalida; no aplicarle caché immutable. R2 requiere configuración y publicación aparte; no se ha activado con este cambio.

## Volver atrás

Quitar un código de `productos` en galerias.json restaura su galería anterior. No editar ni reemplazar a mano productos.json para realizar esa reversión.
