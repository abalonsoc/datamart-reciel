@echo off
REM M7 - Ejecuta el ETL del Data Mart. Lo llama el Programador de tareas de Windows.
REM Funciona desde cualquier ubicación: se mueve a la carpeta donde está este archivo.
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" main.py %*
exit /b %ERRORLEVEL%
