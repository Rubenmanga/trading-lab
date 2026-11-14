@echo off
REM Sesión intradía en vivo. Déjalo abierto hasta que termine solo (cierre forzado).
REM Para parar antes: pulsa Ctrl+C (cierra todas las posiciones).
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
lab intradia sesion
lab diario
pause
