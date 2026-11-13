@echo off
cd /d "%~dp0.."
if not exist "scripts\import_export\sync_word_database.py" (
  echo Word sync script was removed. Use the web editor to update database content.
  exit /b 1
)
".venv\Scripts\python.exe" scripts\import_export\sync_word_database.py --apply
if errorlevel 1 exit /b 1
echo Database updated. Refresh the website to read the new content.
