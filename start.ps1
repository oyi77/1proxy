#!/usr/bin/env pwsh
# 1proxy Platform Startup Script for Windows
# This script starts the entire 1proxy platform with all required services

param(
    [switch]$Docker,
    [switch]$Local,
    [switch]$Help
)

# Color output functions
function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "ℹ️  $msg" -ForegroundColor Cyan }
function Write-Warning { param($msg) Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Header { param($msg) Write-Host "`n🚀 $msg" -ForegroundColor Magenta }

# Help message
if ($Help) {
    Write-Host @"
1proxy Platform Startup Script

USAGE:
    .\start.ps1 [-Docker] [-Local] [-Help]

OPTIONS:
    -Docker     Start using Docker Compose (recommended)
    -Local      Start locally (requires Python 3.12+ and Node.js 18+)
    -Help       Show this help message

EXAMPLES:
    .\start.ps1 -Docker     # Start with Docker
    .\start.ps1 -Local      # Start locally
    .\start.ps1             # Interactive mode (asks which method)

REQUIREMENTS:
    Docker mode: Docker Desktop installed and running
    Local mode:  Python 3.12+, Node.js 18+, pip, npm

"@
    exit 0
}

# Determine startup mode
$mode = $null
if ($Docker) { $mode = "docker" }
elseif ($Local) { $mode = "local" }
else {
    Write-Header "1proxy Platform Startup"
    Write-Host ""
    Write-Host "Select startup mode:"
    Write-Host "  [1] Docker Compose (recommended)"
    Write-Host "  [2] Local Development"
    Write-Host "  [3] Exit"
    Write-Host ""
    $choice = Read-Host "Enter choice (1-3)"
    
    switch ($choice) {
        "1" { $mode = "docker" }
        "2" { $mode = "local" }
        "3" { exit 0 }
        default { 
            Write-Error "Invalid choice. Exiting."
            exit 1
        }
    }
}

# Change to project root
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Header "Starting 1proxy Platform in $mode mode..."

# ============================================================================
# DOCKER MODE
# ============================================================================
if ($mode -eq "docker") {
    Write-Info "Checking Docker installation..."
    
    # Check if Docker is installed
    try {
        $dockerVersion = docker --version
        Write-Success "Docker found: $dockerVersion"
    }
    catch {
        Write-Error "Docker is not installed or not in PATH"
        Write-Info "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    
    # Check if Docker is running
    try {
        docker ps | Out-Null
        Write-Success "Docker daemon is running"
    }
    catch {
        Write-Error "Docker daemon is not running"
        Write-Info "Please start Docker Desktop and try again"
        exit 1
    }
    
    # Check if docker-compose.yml exists
    if (-not (Test-Path "docker-compose.yml")) {
        Write-Error "docker-compose.yml not found in current directory"
        exit 1
    }
    
    # Check for .env file
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found"
        if (Test-Path ".env.example") {
            Write-Info "Creating .env from .env.example..."
            Copy-Item ".env.example" ".env"
            Write-Warning "Please edit .env file with your OAuth credentials before continuing"
            Write-Info "Press any key to continue after editing .env..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    }
    
    Write-Info "Starting Docker Compose services..."
    Write-Host ""
    
    # Start Docker Compose
    docker-compose up --build -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Success "Docker services started successfully!"
        Write-Host ""
        Write-Info "Waiting for services to be ready..."
        Start-Sleep -Seconds 5
        
        # Check service health
        Write-Info "Checking service status..."
        docker-compose ps
        
        Write-Host ""
        Write-Success "1proxy Platform is running!"
        Write-Host ""
        Write-Host "🌐 Frontend:    http://localhost:3000" -ForegroundColor Cyan
        Write-Host "🔧 Backend API: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "📚 API Docs:    http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host "🗄️  Redis:       localhost:6379" -ForegroundColor Cyan
        Write-Host ""
        Write-Info "To view logs: docker-compose logs -f"
        Write-Info "To stop:      docker-compose down"
        Write-Host ""
    }
    else {
        Write-Error "Failed to start Docker services"
        Write-Info "Check logs with: docker-compose logs"
        exit 1
    }
}

# ============================================================================
# LOCAL MODE
# ============================================================================
elseif ($mode -eq "local") {
    Write-Info "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Success "Python found: $pythonVersion"
    }
    catch {
        Write-Error "Python is not installed or not in PATH"
        Write-Info "Please install Python 3.12+ from: https://www.python.org/downloads/"
        exit 1
    }
    
    # Check Node.js
    try {
        $nodeVersion = node --version
        Write-Success "Node.js found: $nodeVersion"
    }
    catch {
        Write-Error "Node.js is not installed or not in PATH"
        Write-Info "Please install Node.js 18+ from: https://nodejs.org/"
        exit 1
    }
    
    # Check npm
    try {
        $npmVersion = npm --version
        Write-Success "npm found: v$npmVersion"
    }
    catch {
        Write-Error "npm is not installed or not in PATH"
        exit 1
    }
    
    Write-Host ""
    Write-Header "Setting up Backend..."
    
    # Copy .env from root to backend if it exists
    if (Test-Path ".env") {
        Write-Info "Copying .env to backend directory..."
        Copy-Item ".env" "1proxy-backend\.env" -Force
        Write-Success ".env synced to backend"
    }
    elseif (-not (Test-Path "1proxy-backend\.env")) {
        Write-Warning "No .env file found. OAuth features will not work."
        Write-Info "Copy .env.example to .env and configure your credentials"
    }
    
    # Backend setup
    Set-Location "1proxy-backend"
    
    # Check if venv exists
    if (-not (Test-Path "venv")) {
        Write-Info "Creating Python virtual environment..."
        python -m venv venv
    }
    
    # Activate venv
    Write-Info "Activating virtual environment..."
    & ".\venv\Scripts\Activate.ps1"
    
    # Upgrade pip first
    Write-Info "Upgrading pip..."
    python -m pip install --upgrade pip --quiet
    
    # Install dependencies
    if (-not (Test-Path "venv\Lib\site-packages\fastapi")) {
        Write-Info "Installing Python dependencies..."
        pip install -r requirements.txt
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install Python dependencies"
            Write-Info "Cleaning up virtual environment..."
            Set-Location $projectRoot
            Remove-Item "1proxy-backend\venv" -Recurse -Force -ErrorAction SilentlyContinue
            Write-Info "Please run the script again to recreate the virtual environment"
            exit 1
        }
    }
    else {
        Write-Success "Python dependencies already installed"
    }
    
    # Check if database exists
    if (-not (Test-Path "data\1proxy.db")) {
        Write-Info "Running database migrations..."
        alembic upgrade head
    }
    else {
        Write-Success "Database already exists"
    }
    
    # Start backend in background
    Write-Info "Starting FastAPI backend..."
    $backendJob = Start-Job -ScriptBlock {
        param($path)
        Set-Location $path
        & ".\venv\Scripts\Activate.ps1"
        python run.py
    } -ArgumentList (Get-Location).Path
    
    Write-Success "Backend started (Job ID: $($backendJob.Id))"
    
    # Wait for backend to be ready
    Write-Info "Waiting for backend to be ready..."
    Start-Sleep -Seconds 5
    
    # Frontend setup
    Set-Location "$projectRoot\1proxy-frontend"
    Write-Host ""
    Write-Header "Setting up Frontend..."
    
    # Install dependencies
    if (-not (Test-Path "node_modules")) {
        Write-Info "Installing Node.js dependencies..."
        npm install
    }
    else {
        Write-Success "Node.js dependencies already installed"
    }
    
    # Start frontend in background
    Write-Info "Starting Next.js frontend..."
    $env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
    $frontendJob = Start-Job -ScriptBlock {
        param($path)
        Set-Location $path
        $env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
        npm run dev
    } -ArgumentList (Get-Location).Path
    
    Write-Success "Frontend started (Job ID: $($frontendJob.Id))"
    
    # Return to project root
    Set-Location $projectRoot
    
    Write-Host ""
    Write-Success "1proxy Platform is running!"
    Write-Host ""
    Write-Host "🌐 Frontend:    http://localhost:3000" -ForegroundColor Cyan
    Write-Host "🔧 Backend API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "📚 API Docs:    http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Info "Backend Job ID:  $($backendJob.Id)"
    Write-Info "Frontend Job ID: $($frontendJob.Id)"
    Write-Host ""
    Write-Warning "Press Ctrl+C to stop all services"
    Write-Host ""
    
    # Monitor jobs
    try {
        while ($true) {
            Start-Sleep -Seconds 2
            
            # Check if jobs are still running
            $backendState = (Get-Job -Id $backendJob.Id).State
            $frontendState = (Get-Job -Id $frontendJob.Id).State
            
            if ($backendState -eq "Failed") {
                Write-Error "Backend job failed!"
                Receive-Job -Id $backendJob.Id
                break
            }
            
            if ($frontendState -eq "Failed") {
                Write-Error "Frontend job failed!"
                Receive-Job -Id $frontendJob.Id
                break
            }
        }
    }
    finally {
        # Cleanup
        Write-Host ""
        Write-Info "Stopping services..."
        Stop-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
        Stop-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue
        Remove-Job -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
        Remove-Job -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
        Write-Success "All services stopped"
    }
}
