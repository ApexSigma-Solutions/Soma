# =============================================================================
# OmegaKG Multi-Project Run Script (PowerShell)
# =============================================================================
# Runs the full OmegaKG stack including capture server and memos.MCP.
#
# Usage:
#   .\scripts\run-multi-project.ps1              # Start all services
#   .\scripts\run-multi-project.ps1 stop         # Stop all services
#   .\scripts\run-multi-project.ps1 memos-mcp    # Start only memos.MCP
#   .\scripts\run-multi-project.ps1 capture      # Start only capture server
# =============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$Command = if ($args.Count -gt 0) { $args[0] } else { "all" }

Push-Location $ProjectRoot

switch ($Command) {
  {$_ -eq "all" -or $_ -eq "start"} {
    Write-Host "Starting OmegaKG multi-project stack..." -ForegroundColor Green
    docker-compose up -d
    Write-Host ""
    Write-Host "✓ Services started:" -ForegroundColor Green
    Write-Host "  - OmegaKG Capture: http://localhost:8765" -ForegroundColor Cyan
    Write-Host "  - MemOS MCP:      http://localhost:8768" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "View logs: docker-compose logs -f" -ForegroundColor Cyan
    Write-Host "Stop: .\scripts\run-multi-project.ps1 stop" -ForegroundColor Cyan
  }
  "stop" {
    Write-Host "Stopping OmegaKG multi-project stack..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✓ All services stopped" -ForegroundColor Green
  }
  "restart" {
    Write-Host "Restarting OmegaKG multi-project stack..." -ForegroundColor Yellow
    docker-compose restart
    Write-Host "✓ All services restarted" -ForegroundColor Green
  }
  "memos-mcp" {
    Write-Host "Starting memos.MCP only..." -ForegroundColor Green
    docker-compose up -d memos-mcp
    Write-Host "✓ MemOS MCP started on http://localhost:8768" -ForegroundColor Green
  }
  {$_ -eq "omega-capture" -or $_ -eq "capture"} {
    Write-Host "Starting OmegaKG capture server only..." -ForegroundColor Green
    docker-compose up -d omega-capture
    Write-Host "✓ OmegaKG Capture started on http://localhost:8765" -ForegroundColor Green
  }
  "logs" {
    if ($args.Count -gt 1) {
      docker-compose logs -f $args[1]
    } else {
      docker-compose logs -f
    }
  }
  "status" {
    docker-compose ps
  }
  default {
    Write-Host "Usage: .\scripts\run-multi-project.ps1 {all|stop|restart|memos-mcp|capture|logs|status}" -ForegroundColor Red
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  all, start     - Start all services (default)"
    Write-Host "  stop           - Stop all services"
    Write-Host "  restart        - Restart all services"
    Write-Host "  memos-mcp      - Start only memos.MCP"
    Write-Host "  capture        - Start only capture server"
    Write-Host "  logs [service] - View logs (optionally for specific service)"
    Write-Host "  status         - Show service status"
    exit 1
  }
}

Pop-Location
