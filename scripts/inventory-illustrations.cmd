@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\backend"
set "PYTHONIOENCODING=utf-8"
"%CD%\.venv\Scripts\python.exe" "%CD%\scripts\content\inventory_illustrations.py" %*
exit /b %errorlevel%
