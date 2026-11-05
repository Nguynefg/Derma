@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\import_export\sync_word_database.py --apply
if errorlevel 1 exit /b 1
echo Database updated. Refresh the website to read the new content.
