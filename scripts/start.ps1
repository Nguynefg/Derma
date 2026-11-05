param([int]$Port = 8000, [string]$Python = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    if (-not $Python) {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCommand) { $Python = $pythonCommand.Source }
        else {
            $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
            if (Test-Path $bundledPython) { $Python = $bundledPython }
            else { throw 'Install Python 3.11+ or pass -Python with its executable path.' }
        }
    }
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
}
$projectPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
$requirements = 'backend/requirements/base.txt'
if ((Test-Path 'backend/database.local.json') -or $env:DERMA_DATABASE_CONFIG -or $env:DATABASE_URL) {
    $requirements = 'backend/requirements/sqlserver.txt'
}
& $projectPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
if ((Test-Path 'backend/models/active/model-card.json') -or $env:DERMA_IMAGE_MODEL_CARD) {
    & $projectPython -m pip install -r backend/requirements/image.txt
    if ($LASTEXITCODE -ne 0) { throw 'Image runtime installation failed.' }
}
Push-Location frontend
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
Set-Location backend
$env:ALLOWED_ORIGINS = "http://127.0.0.1:$Port,http://localhost:$Port"
Write-Host "Derma: http://127.0.0.1:$Port"
& $projectPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port --no-access-log
