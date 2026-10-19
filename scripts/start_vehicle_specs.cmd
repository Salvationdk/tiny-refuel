@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 (
  python scripts\scrape_vehicle_specs.py --catalog katalog-ufiltreret.json --official-batch --open-ev --engine-data --output resultater
) else (
  py -3 scripts\scrape_vehicle_specs.py --catalog katalog-ufiltreret.json --official-batch --open-ev --engine-data --output resultater
)
if errorlevel 1 (
  echo.
  echo Der opstod en fejl. Se beskeden ovenfor. Gennemfoerte resultater er bevaret.
) else (
  echo.
  echo Faerdig. Se resultater\summary.json og resultater\all-candidates.json.
)
pause
