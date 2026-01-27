# =============================================================================
# MemOS MCP Standalone Run Script (PowerShell)
# =============================================================================
# Runs memos.MCP as a standalone Docker service with SQLite.
#
# Usage:
#   .\scripts\run-standalone.ps1        # Start
#   .\scripts\run-standalone.ps1 stop   # Stop
#   .\scripts\run-standalone.ps1 logs   # View logs
# =============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$Command = if ($args.Count -gt 0) { $args[0] } else { "start" }

Push-Location $ProjectRoot

switch ($Command) {
  "start" {
    Write-Host "Starting memos.MCP standalone..." -ForegroundColor Green
    docker-compose -f docker/docker-compose.yml up -d
    Write-Host "✓ memos.MCP started on http://localhost:8768" -ForegroundColor Green
    Write-Host ""
    Write-Host "View logs: docker-compose -f docker/docker-compose.yml logs -f" -ForegroundColor Cyan
    Write-Host "Stop: .\scripts\run-standalone.ps1 stop" -ForegroundColor Cyan
  }
  "stop" {
    Write-Host "Stopping memos.MCP standalone..." -ForegroundColor Yellow
    docker-compose -f docker/docker-compose.yml down
    Write-Host "✓ memos.MCP stopped" -ForegroundColor Green
  }
  "restart" {
    Write-Host "Restarting memos.MCP standalone..." -ForegroundColor Yellow
    docker-compose -f docker/docker-compose.yml restart
    Write-Host "✓ memos.MCP restarted" -ForegroundColor Green
  }
  "logs" {
    docker-compose -f docker/docker-compose.yml logs -f
  }
  "status" {
    docker-compose -f docker/docker-compose.yml ps
  }
  default {
    Write-Host "Usage: .\scripts\run-standalone.ps1 {start|stop|restart|logs|status}" -ForegroundColor Red
    exit 1
  }
}

Pop-Location
