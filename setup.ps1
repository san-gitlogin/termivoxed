#!/usr/bin/env pwsh
# TermiVoxed - Windows PowerShell Setup Script
# Author: Santhosh T
#
# This script sets up the TermiVoxed on Windows systems using PowerShell

Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "TermiVoxed - Setup"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
Write-Host "[1/6] Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host $pythonVersion -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8 or higher from https://www.python.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if FFmpeg is installed
Write-Host ""
Write-Host "[2/6] Checking FFmpeg installation..." -ForegroundColor Yellow
try {
    $ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host "FFmpeg found!" -ForegroundColor Green
} catch {
    Write-Host "WARNING: FFmpeg is not installed or not in PATH" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install FFmpeg:" -ForegroundColor Yellow
    Write-Host "  1. Download from https://ffmpeg.org/download.html"
    Write-Host "  2. Extract to a folder"
    Write-Host "  3. Add the bin folder to your system PATH"
    Write-Host ""
    Write-Host "Or use Chocolatey: choco install ffmpeg" -ForegroundColor Cyan
    Write-Host "Or use Scoop: scoop install ffmpeg" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter to continue"
}

# Create virtual environment
Write-Host ""
Write-Host "[3/6] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "[4/6] Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host ""
Write-Host "[5/6] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host ""
Write-Host "[6/6] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create storage directories
Write-Host ""
Write-Host "Creating storage directories..." -ForegroundColor Yellow
$directories = @(
    "storage\projects",
    "storage\temp",
    "storage\cache",
    "storage\output",
    "storage\fonts",
    "logs"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "Storage directories created" -ForegroundColor Green

# Copy .env.example to .env if not exists
Write-Host ""
Write-Host "Setting up environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env file created from template" -ForegroundColor Green
    Write-Host "Please edit .env file if you need to customize paths" -ForegroundColor Cyan
} else {
    Write-Host ".env file already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "Setup Complete!"  -ForegroundColor Green
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the application:" -ForegroundColor Yellow
Write-Host "  1. Activate virtual environment: .\venv\Scripts\Activate.ps1"
Write-Host "  2. Run the editor: python main.py"
Write-Host ""
Write-Host "Or simply run: .\run.ps1" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
