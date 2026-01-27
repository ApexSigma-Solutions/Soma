#!/usr/bin/env pwsh
# Complete Startup - All Services
$ErrorActionPreference = "Stop"
Set-Location "d:\projects\Omega_KG_stable"

# Check if server is already running
$serverRunning = Test-NetConnection -ComputerName localhost -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($serverRunning) {
    Write-Host "✓ Server already running on http://localhost:8765" -ForegroundColor Green
    Write-Host "  Use .\stop-all.ps1 first if you need to restart" -ForegroundColor Gray
    exit 0
}

Write-Host "🚀 Starting All Omega KG Services
" -ForegroundColor Cyan

# Start databases
Write-Host "Step 1: Starting databases..." -ForegroundColor Magenta
& .\start-database.ps1

# Wait for databases
Write-Host "`nStep 2: Waiting for databases to be ready..." -ForegroundColor Magenta
Start-Sleep -Seconds 5

# Start capture server
Write-Host "`nStep 3: Starting capture server..." -ForegroundColor Magenta
& .\start-server.ps1
