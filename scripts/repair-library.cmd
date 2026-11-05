@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\maintenance\repair_library_metadata.py --apply
if errorlevel 1 exit /b 1
echo Metadata corrected. Restart the web server to load the updated backend.
