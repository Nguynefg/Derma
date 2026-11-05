@echo off
setlocal
cd /d "%~dp0.."
if errorlevel 1 goto directory_error

where npm.cmd >nul 2>nul
if errorlevel 1 goto node_error

if exist ".venv\Scripts\python.exe" goto environment_ready
where python.exe >nul 2>nul
if errorlevel 1 goto bundled_python
set "DERMA_PYTHON=python.exe"
goto python_ready

:bundled_python
set "DERMA_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%DERMA_PYTHON%" goto python_error

:python_ready
"%DERMA_PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto python_error
if /i "%~1"=="--check" goto check_ok
echo Creating Python environment...
"%DERMA_PYTHON%" -m venv .venv
if errorlevel 1 goto environment_error

:environment_ready
set "DERMA_PYTHON=%CD%\.venv\Scripts\python.exe"
if /i "%~1"=="--check" goto check_ok
echo Installing backend dependencies...
set "DERMA_REQUIREMENTS=backend\requirements\base.txt"
if exist "backend\database.local.json" set "DERMA_REQUIREMENTS=backend\requirements\sqlserver.txt"
if defined DERMA_DATABASE_CONFIG set "DERMA_REQUIREMENTS=backend\requirements\sqlserver.txt"
if defined DATABASE_URL set "DERMA_REQUIREMENTS=backend\requirements\sqlserver.txt"
"%DERMA_PYTHON%" -m pip install --disable-pip-version-check --no-cache-dir -r "%DERMA_REQUIREMENTS%"
if errorlevel 1 goto backend_error

set "DERMA_IMAGE_RUNTIME=0"
if exist "backend\models\active\model-card.json" set "DERMA_IMAGE_RUNTIME=1"
if defined DERMA_IMAGE_MODEL_CARD set "DERMA_IMAGE_RUNTIME=1"
if "%DERMA_IMAGE_RUNTIME%"=="0" goto image_runtime_ready
"%DERMA_PYTHON%" -m pip install --disable-pip-version-check --no-cache-dir -r backend\requirements\image.txt
if errorlevel 1 goto backend_error
:image_runtime_ready

pushd frontend
echo Installing frontend dependencies...
call npm.cmd ci --cache "%CD%\.npm-cache" --no-audit --no-fund
if errorlevel 1 goto frontend_error
call npm.cmd run build
if errorlevel 1 goto frontend_error
popd

set "ALLOWED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000"
cd backend
echo.
echo Derma: http://127.0.0.1:8000
echo Keep this window open. Press Ctrl+C to stop the server.
"%DERMA_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
exit /b %errorlevel%

:check_ok
echo Python and npm are available. This launcher does not use PowerShell.
exit /b 0
:directory_error
echo ERROR: Cannot open the project directory.
exit /b 1
:node_error
echo ERROR: Install Node.js 22 or newer, then reopen Command Prompt.
exit /b 1
:python_error
echo ERROR: Install Python 3.11 or newer and add it to PATH, then reopen Command Prompt.
exit /b 1
:environment_error
echo ERROR: Could not create the Python environment.
exit /b 1
:backend_error
echo ERROR: Backend installation failed. See the error above.
exit /b 1
:frontend_error
popd
echo ERROR: Frontend installation or build failed. See the error above.
exit /b 1
