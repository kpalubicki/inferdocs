#!/bin/bash
# InferDocs - Linux/Ubuntu Startup Script
# Prerequisites: Python 3.11+, Ollama installed (optional)

set -e

echo "=================================="
echo "  InferDocs - Linux Setup"
echo "=================================="
echo ""

# Check Python version
echo "[1/5] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.11+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "Found: $PYTHON_VERSION"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "[2/5] Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "[2/5] Virtual environment already exists"
fi

# Activate virtual environment
echo "[3/5] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "[4/5] Installing dependencies..."
pip install -e ".[dev]"
echo "Dependencies installed"

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo ".env file created"
fi

# Check if Ollama is running
echo "[5/5] Checking Ollama status..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama is running"
else
    echo "WARNING: Ollama not detected at http://localhost:11434"
    echo "Please start Ollama before using the application"
    echo "Install: curl -fsSL https://ollama.ai/install.sh | sh"
fi

echo ""
echo "=================================="
echo "  Setup Complete!"
echo "=================================="
echo ""
echo "Starting InferDocs..."
echo "API will be available at: http://localhost:8000"
echo "Playground: http://localhost:8000/playground"
echo "API Docs: http://localhost:8000/docs"
echo ""

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
