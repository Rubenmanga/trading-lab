@echo off
REM Botón del pánico: cierra TODO en la cuenta demo de Alpaca.
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
lab intradia cerrar-todo
pause
