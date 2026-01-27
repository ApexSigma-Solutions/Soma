#!/usr/bin/env pwsh
# Stop All Omega KG Services
$ErrorActionPreference = "Stop"
Set-Location "d:\projects\Omega_KG_stable"

Write-Host "🛑 Stopping Omega KG Services..." -ForegroundColor Yellow

# Stop Python processes
Get-Process -Name "python" -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -like "*capture_server*" } | 
    Stop-Process -Force

# Stop Docker services
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker-compose down
    Write-Host "✓ Docker services stopped" -ForegroundColor Green
}

Write-Host "✓ All services stopped" -ForegroundColor Green
