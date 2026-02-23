Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path ".venv")) {
    throw "Virtual environment not found. Run .\setup.ps1 first."
}

. ".\.venv\Scripts\Activate.ps1"
python backend\app.py
