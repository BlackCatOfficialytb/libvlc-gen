#!/usr/bin/env pwsh
# setup-venv.ps1 - Create .venv and install dependencies (Windows)

$VenvDir = ".venv"

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment in $VenvDir..."
    python -m venv $VenvDir
}

Write-Host "Activating virtual environment..."
& "$VenvDir\Scripts\Activate.ps1"

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host ""
Write-Host "Virtual environment ready!"
Write-Host "Activate with: .venv\Scripts\Activate.ps1"
Write-Host "Run generator: python tools/generate_libvlc.py --help"