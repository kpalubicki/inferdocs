# InferDocs - Windows Startup Script
# Prerequisites: Python 3.11+, Ollama installed

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  InferDocs - Windows Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "[1/5] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Create virtual environment if not exists
if (-Not (Test-Path "venv")) {
    Write-Host "[2/5] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[2/5] Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "[3/5] Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "[4/5] Installing dependencies..." -ForegroundColor Yellow
pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "Dependencies installed" -ForegroundColor Green

# Create .env if not exists
if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host ".env file created" -ForegroundColor Green
}

# Check if Ollama is running
Write-Host "[5/5] Checking Ollama status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 2
    Write-Host "Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Ollama not detected at http://localhost:11434" -ForegroundColor Yellow
    Write-Host "Please start Ollama before using the application" -ForegroundColor Yellow
    Write-Host "Download: https://ollama.ai/" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting InferDocs..." -ForegroundColor Yellow
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Playground: http://localhost:8000/playground" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
