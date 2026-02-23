Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Step
    )

    Write-Host $Step -ForegroundColor Yellow
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Failed at step: $Step"
    }
}

Write-Host "=== SmartVision Setup (Windows PowerShell) ===" -ForegroundColor Cyan

$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py -3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} else {
    throw "Python is not installed or not available in PATH. Install Python 3.10+ first."
}

if (-not (Test-Path ".venv")) {
    Invoke-Checked -Command "$pythonCmd -m venv .venv" -Step "Creating virtual environment..."
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. ".\.venv\Scripts\Activate.ps1"

Invoke-Checked -Command "python -m pip install --upgrade pip" -Step "Upgrading pip..."
Invoke-Checked -Command "pip install -r requirements.txt" -Step "Installing dependencies..."

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example" -ForegroundColor Green
        Write-Host "Please edit .env before running in production." -ForegroundColor Yellow
    } else {
        Write-Host ".env.example not found. Skipping .env creation." -ForegroundColor Yellow
    }
} else {
    Write-Host ".env already exists. Keeping current values." -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next commands:" -ForegroundColor Cyan
Write-Host "1) .\.venv\Scripts\Activate.ps1"
Write-Host "2) python backend\app.py"
