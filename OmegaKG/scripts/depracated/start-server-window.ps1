#!/usr/bin/env pwsh
# Auto-generated startup script for Task Scheduler
$ErrorActionPreference = "Stop"

# Set window title
$host.UI.RawUI.WindowTitle = "Omega KG Capture Server"

# Change to project directory
Set-Location "d:\projects\Omega_KG_stable"

# Check if server is already running
$serverRunning = Test-NetConnection -ComputerName localhost -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($serverRunning) {
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║   Omega KG Capture Server - ALREADY RUNNING                  ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "✓ Server is already running on http://localhost:8765" -ForegroundColor Green
    Write-Host "  This window will close in 5 seconds..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    exit 0
}

# Clear Python cache
Get-ChildItem -Path omega_kg -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path omega_kg -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Omega KG Capture Server - Auto-Started              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Start databases if not running
$neo4j = docker ps --filter "name=neo4j.stable" --format "{{.Names}}" | Select-String "neo4j"
$postgres = docker ps --filter "name=postgres.stable" --format "{{.Names}}" | Select-String "postgres"

if (-not $neo4j -or -not $postgres) {
    Write-Host "🐳 Starting databases..." -ForegroundColor Yellow
    docker-compose up -d postgres neo4j
    Write-Host "⏳ Waiting for databases to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 8
}

Write-Host "🚀 Starting Omega KG Capture Server..." -ForegroundColor Cyan
Write-Host "   Server URL: http://localhost:8765" -ForegroundColor White
Write-Host "   Press Ctrl+C to stop, or close this window to exit" -ForegroundColor Yellow
Write-Host ""

# Start the server
poetry run python omega_kg/capture_server.py

# Keep window open if server crashes
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Server exited with error code $LASTEXITCODE" -ForegroundColor Red
    Write-Host "Press any key to close..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
