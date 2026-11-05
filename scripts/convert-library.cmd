@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\content\convert_library_articles.py
if errorlevel 1 exit /b 1
echo Library conversion completed.
