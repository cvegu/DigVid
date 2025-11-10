@echo off
REM Script para iniciar el servidor DigVid en Windows

cd /d "%~dp0"

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause

