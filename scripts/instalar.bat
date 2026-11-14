@echo off
REM Instala el proyecto en Windows. Doble clic o ejecútalo desde la carpeta del repo.
cd /d "%~dp0.."
python -m venv .venv || (echo Necesitas instalar Python 3.11 o superior desde python.org & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .[dev]
if not exist .env copy .env.example .env
echo.
echo Listo. Ahora abre el archivo .env con el Bloc de notas y pon tus claves de Alpaca PAPER.
pause
