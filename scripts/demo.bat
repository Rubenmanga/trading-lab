@echo off
REM Prueba completa con datos inventados y abre el panel. No necesita claves.
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
lab intradia demo
lab panel
