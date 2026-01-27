# =============================================================================
# MemOS MCP Docker Build Script (PowerShell)
# =============================================================================
# Builds the memos-mcp Docker image from the project root.
#
# Usage:
#   .\scripts\build.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "Building memos-mcp Docker image..." -ForegroundColor Green
Write-Host "Project root: $ProjectRoot" -ForegroundColor Cyan

Push-Location $ProjectRoot

docker build `
  -f docker/Dockerfile `
  -t memos-mcp:latest `
  .

Pop-Location

Write-Host "✓ Build complete: memos-mcp:latest" -ForegroundColor Green
