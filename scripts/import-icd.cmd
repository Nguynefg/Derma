@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" -X utf8 "scripts\import_export\import_icd.py" --apply
if errorlevel 1 (
  echo Import failed. Existing article and user data were not changed.
  exit /b 1
)
echo ICD import completed. See storage\imports\icd-import\import-result.json
