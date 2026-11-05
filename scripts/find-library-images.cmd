@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" exit /b 1
.venv\Scripts\python.exe scripts\content\read_library_for_images.py
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe scripts\content\index_medical_images.py
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe scripts\content\stage_disease_images.py
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe scripts\content\audit_disease_images.py
exit /b %errorlevel%
