@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Python environment .venv was not found.
  exit /b 1
)
".venv\Scripts\python.exe" "%~dp0maintenance\cleanup_unused_files.py" %*
exit /b %errorlevel%
