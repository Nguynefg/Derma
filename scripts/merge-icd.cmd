@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" -X utf8 "scripts\import_export\merge_icd.py"
if errorlevel 1 (
  echo Merge failed. See the error above. Do not manually delete the ICD tables.
  exit /b 1
)
echo ICD tables consolidated. See storage\imports\icd-import\merge-result.json
