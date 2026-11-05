@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\maintenance\fix_remaining_library.py --apply
if errorlevel 1 exit /b 1
echo Cleanup committed. Restart the web server to use the updated source and ID resolution code.
