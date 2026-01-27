#!/usr/bin/env pwsh
# Check Omega KG Status
$ErrorActionPreference = "Continue"
Set-Location "d:\projects\Omega_KG_stable"

Write-Host "Omega KG System Status
" -ForegroundColor Cyan
Write-Host ("=" * 60)

# Check .env
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "✗ .env file missing" -ForegroundColor Red
}

# Check virtual environment
if (Test-Path ".venv") {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "✗ Virtual environment missing" -ForegroundColor Red
}

# Check Docker services
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $neo4j = docker ps --filter "name=neo4j" --format "{{.Names}}" | Select-String "neo4j"
    $postgres = docker ps --filter "name=postgres" --format "{{.Names}}" | Select-String "postgres"
    
    if ($neo4j) {
        Write-Host "✓ Neo4j container running" -ForegroundColor Green
    } else {
        Write-Host "✗ Neo4j container not running" -ForegroundColor Red
    }
    
    if ($postgres) {
        Write-Host "✓ PostgreSQL container running" -ForegroundColor Green
    } else {
        Write-Host "✗ PostgreSQL container not running" -ForegroundColor Red
    }
} else {
    Write-Host "⚠ Docker not available" -ForegroundColor Yellow
}

# Check capture server
$captureServer = Get-Process -Name "python" -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -like "*capture_server*" }
    
if ($captureServer) {
    Write-Host "✓ Capture server running" -ForegroundColor Green
} else {
    Write-Host "✗ Capture server not running" -ForegroundColor Red
}

Write-Host ("=" * 60)
