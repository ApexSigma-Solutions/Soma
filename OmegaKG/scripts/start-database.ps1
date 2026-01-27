#!/usr/bin/env pwsh
# Start Docker Services (Neo4j + PostgreSQL)
$ErrorActionPreference = "Stop"
$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

Write-Host "🐳 Starting Docker services..." -ForegroundColor Cyan

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker-compose up -d neo4j postgres
    
    Write-Host "`n✓ Services started:" -ForegroundColor Green
    Write-Host "  - Neo4j:      bolt://localhost:7687" -ForegroundColor Cyan
    Write-Host "  - PostgreSQL: localhost:5433" -ForegroundColor Cyan
    Write-Host "  - Neo4j UI:   http://localhost:7474" -ForegroundColor Cyan
    
    Write-Host "`nℹ Check status with: docker-compose ps" -ForegroundColor Yellow
} else {
    Write-Host "❌ Docker not found! Please install Docker Desktop." -ForegroundColor Red
    Write-Host "   Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
}
