#!/usr/bin/env pwsh
# Quick Start - Omega KG Capture Server (launches in new window)
$ErrorActionPreference = "Stop"
Set-Location "d:\projects\Omega_KG_stable"

# Check if server is already running
$serverRunning = Test-NetConnection -ComputerName localhost -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($serverRunning) {
    Write-Host "✓ Server already running on http://localhost:8765" -ForegroundColor Green
    Write-Host "  Use 'Stop-Process -Name python' to stop it first if needed" -ForegroundColor Gray
    exit 0
}

# Launch server in separate window
Write-Host "🚀 Launching Omega KG Capture Server in new window..." -ForegroundColor Cyan
Write-Host "   Server will run on http://localhost:8765" -ForegroundColor Yellow
Write-Host ""

Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\start-server-window.ps1"

# Wait a moment and verify
Start-Sleep -Seconds 3
$serverRunning = Test-NetConnection -ComputerName localhost -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($serverRunning) {
    Write-Host "✓ Server started successfully!" -ForegroundColor Green
} else {
    Write-Host "⏳ Server is starting... (check the new window)" -ForegroundColor Yellow
}
