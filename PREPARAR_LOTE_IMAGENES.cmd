@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo DECU - Preparar imagenes por lotes
echo Se leeran los JPG originales y se crearan copias WebP para la web.
echo.
set /p "DECU_CODIGOS=Codigos separados por espacios (por ejemplo 520 817): "
if not defined DECU_CODIGOS exit /b 1
powershell -NoProfile -Command "if ($env:DECU_CODIGOS -notmatch '^\d+(\s+\d+)*$') { exit 1 }"
if errorlevel 1 (
  echo Solo se admiten numeros separados por espacios.
  pause
  exit /b 1
)
python preparar_imagenes_web.py --origen "C:\1. COPIA DE SEGURIDAD PC 2018\DECU 2025\02. FABRICA DE MODELOS\02. MOCK UP CON PERSPECTIVA" --codigos %DECU_CODIGOS%
if errorlevel 1 (
  echo No se actualizo el lote. Revisar el mensaje anterior.
) else (
  echo Lote listo. Publicar media/catalogo y galerias.json con GitHub Desktop.
)
pause
