@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" "scripts\content\apply_content_completion.py" --include-nci --apply
if errorlevel 1 exit /b 1
echo Content completion processed. See the actual applied counts above.
