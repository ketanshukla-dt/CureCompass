param(
    [switch]$SkipFrontend
)

Write-Host ""
Write-Host "[FixIQ] - Intelligent Incident Remediation Platform"
Write-Host "=================================================="
Write-Host ""

if (-not (Test-Path .env)) {
    Write-Host "[Warning] No .env found. Copying .env.example -> .env"
    Copy-Item .env.example .env
    Write-Host "   Edit .env with your Dynatrace + Anthropic credentials, then re-run."
    Write-Host ""
}

$pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $pythonExe = $pyLauncher.Source
    $pythonArgs = "-3.12"
} else {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "Python 3.11 or 3.12 is required. Install it and rerun this script."
        exit 1
    }
    $pythonExe = $python.Source
    $pythonArgs = $null
}

Write-Host "[Info] Installing Python dependencies..."
if ($pythonArgs) {
    & $pythonExe $pythonArgs -m pip install --upgrade pip
    & $pythonExe $pythonArgs -m pip install -r requirements.txt
} else {
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r requirements.txt
}

if (-not $SkipFrontend) {
    if (-not (Test-Path "static")) {
        Write-Host ""
        Write-Host "[Info] Building React frontend..."
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            Write-Error "npm is required to build the frontend. Install Node.js and rerun."
            exit 1
        }

        Push-Location frontend
        npm install --silent
        npm run build
        Pop-Location
        Write-Host "   [Success] Frontend built -> static/"
    }
}

Write-Host ""
Write-Host "Starting FixIQ..."
Write-Host "   Visit: http://localhost:8000"
Write-Host "   API Docs: http://localhost:8000/docs"
Write-Host ""

if ($pythonArgs) {
    & $pythonExe $pythonArgs main.py
} else {
    & $pythonExe main.py
}
