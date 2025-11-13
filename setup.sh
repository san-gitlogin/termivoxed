#!/bin/bash

# Console Video Editor - Unix/Linux/macOS Setup Script
# Author: Santhosh T
#
# This script sets up the Console Video Editor on Unix-like systems

echo ""
echo "========================================"
echo "Console Video Editor - Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"
echo ""

# Check FFmpeg
echo "Checking FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    ffmpeg_version=$(ffmpeg -version 2>&1 | head -n 1)
    echo "✓ FFmpeg installed: $ffmpeg_version"
else
    echo "✗ FFmpeg not found!"
    echo "  Please install FFmpeg:"
    echo "    macOS: brew install ffmpeg"
    echo "    Ubuntu: sudo apt-get install ffmpeg"
    exit 1
fi
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create .env file
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi
echo ""

# Create storage directories
echo "Creating storage directories..."
mkdir -p storage/{projects,temp,cache,output,fonts}
mkdir -p logs
echo "✓ Storage directories created"
echo ""

echo "=========================================="
echo "✓ Setup complete!"
echo ""
echo "To start the editor:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo "  2. Run the editor:"
echo "     python main.py"
echo ""
echo "Happy editing! 🎬"
