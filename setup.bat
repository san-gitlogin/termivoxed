@echo off
REM Console Video Editor - Windows Setup Script
REM Author: Santhosh T
REM
REM This script sets up the Console Video Editor on Windows systems

echo.
echo ========================================
echo Console Video Editor - Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/6] Checking Python version...
python --version

REM Check if FFmpeg is installed
echo.
echo [2/6] Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg is not installed or not in PATH
    echo.
    echo Please install FFmpeg:
    echo   1. Download from https://ffmpeg.org/download.html
    echo   2. Extract to a folder
    echo   3. Add the bin folder to your system PATH
    echo.
    echo Or use Chocolatey: choco install ffmpeg
    echo.
    pause
) else (
    echo FFmpeg found!
)

REM Create virtual environment
echo.
echo [3/6] Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists
) else (
    python -m venv venv
    echo Virtual environment created
)

REM Activate virtual environment
echo.
echo [4/6] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo [5/6] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo [6/6] Installing dependencies...
pip install -r requirements.txt

REM Create storage directories
echo.
echo Creating storage directories...
if not exist "storage\projects" mkdir storage\projects
if not exist "storage\temp" mkdir storage\temp
if not exist "storage\cache" mkdir storage\cache
if not exist "storage\output" mkdir storage\output
if not exist "storage\fonts" mkdir storage\fonts
if not exist "logs" mkdir logs

REM Copy .env.example to .env if not exists
echo.
echo Setting up environment configuration...
if not exist ".env" (
    copy .env.example .env
    echo .env file created from template
    echo Please edit .env file if you need to customize paths
) else (
    echo .env file already exists
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To run the application:
echo   1. Activate virtual environment: venv\Scripts\activate.bat
echo   2. Run the editor: python main.py
echo.
echo Or simply run: run.bat
echo.
pause
