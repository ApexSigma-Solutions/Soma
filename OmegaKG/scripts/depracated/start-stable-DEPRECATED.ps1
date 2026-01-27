#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Omega_KG Stable/Production Environment Bootstrap Script
.DESCRIPTION
    Sets OS environment variables, activates venv, verifies infrastructure, and starts the capture server.
    Run from: d:\projects\Omega_KG_stable\
.EXAMPLE
    .\scripts\start-stable.ps1
    .\scripts\start-stable.ps1 -SkipChecks
#>

[CmdletBinding()]
param(
    [switch]$SkipChecks,
    [switch]$BackgroundMode
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host " Omega_KG STABLE Environment Bootstrap" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════════
# 1. HARD-RESET ENVIRONMENT VARIABLES TO STABLE VALUES
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "🔧 Setting STABLE environment variables..." -ForegroundColor Yellow

$env:OMEGA_ENV       = 'stable'
$env:POSTGRES_DB     = 'omega_kg_stable'
$env:POSTGRES_PORT   = '5433'
$env:POSTGRES_SERVER = '127.0.0.1'
$env:POSTGRES_USER   = 'omega_user'
$env:APP_PORT        = '8002'
$env:APP_HOST        = '127.0.0.1'
$env:APP_ENV         = 'stable'
$env:NEO4J_URI       = 'bolt://localhost:7687'

# BWS Token - use STABLE-specific token if available
if ($env:BWS_ACCESS_TOKEN_STABLE) {
    $env:BWS_ACCESS_TOKEN = $env:BWS_ACCESS_TOKEN_STABLE
}

Write-Host "  ├─ OMEGA_ENV:      $env:OMEGA_ENV" -ForegroundColor DarkGray
Write-Host "  ├─ POSTGRES_DB:    $env:POSTGRES_DB" -ForegroundColor DarkGray
Write-Host "  ├─ POSTGRES_PORT:  $env:POSTGRES_PORT" -ForegroundColor DarkGray
Write-Host "  ├─ APP_PORT:       $env:APP_PORT" -ForegroundColor DarkGray
Write-Host "  ├─ NEO4J_URI:      $env:NEO4J_URI" -ForegroundColor DarkGray
Write-Host "  └─ BWS_TOKEN:      $(if($env:BWS_ACCESS_TOKEN){'Present'}else{'Not set'})" -ForegroundColor DarkGray
Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════════
# 2. CHANGE TO PROJECT ROOT
# ═══════════════════════════════════════════════════════════════════════════════
Set-Location $ProjectRoot
Write-Host "📁 Working directory: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════════
# 3. LOAD .env FILE (FALLBACK VALUES)
# ═══════════════════════════════════════════════════════════════════════════════
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "📄 Loading .env file (fallback values)..." -ForegroundColor Yellow
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$' -and $_ -notmatch '^\s*#') {
            $varName = $Matches[1]
            $varValue = $Matches[2].Trim('"').Trim("'")
            # Only set if not already set (preserve explicit overrides)
            if (-not (Get-Item "Env:$varName" -ErrorAction SilentlyContinue)) {
                Set-Item -Path "Env:$varName" -Value $varValue
            }
        }
    }
    Write-Host "  └─ Loaded $(Get-Content $envFile | Where-Object {$_ -match '^\s*[A-Za-z]' -and $_ -notmatch '^\s*#'} | Measure-Object | Select-Object -ExpandProperty Count) variables" -ForegroundColor DarkGray
    Write-Host ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4. PRE-FLIGHT INFRASTRUCTURE CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
if (-not $SkipChecks) {
    Write-Host "🔍 Running pre-flight infrastructure checks..." -ForegroundColor Yellow
    $allPassed = $true

    # PostgreSQL check (port 5433)
    $pgCheck = Test-NetConnection -ComputerName localhost -Port 5433 -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($pgCheck) {
        Write-Host "  ✅ PostgreSQL STABLE (port 5433) - LISTENING" -ForegroundColor Green
    } else {
        Write-Host "  ❌ PostgreSQL STABLE (port 5433) - NOT LISTENING" -ForegroundColor Red
        Write-Host "     Run: docker-compose up -d postgres" -ForegroundColor DarkGray
        $allPassed = $false
    }

    # Neo4j check (bolt port 7687)
    $neo4jCheck = Test-NetConnection -ComputerName localhost -Port 7687 -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($neo4jCheck) {
        Write-Host "  ✅ Neo4j STABLE (bolt 7687) - LISTENING" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Neo4j STABLE (bolt 7687) - NOT LISTENING" -ForegroundColor Red
        Write-Host "     Run: docker-compose up -d neo4j" -ForegroundColor DarkGray
        $allPassed = $false
    }

    # Ollama check (optional)
    $ollamaCheck = Test-NetConnection -ComputerName localhost -Port 11434 -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($ollamaCheck) {
        Write-Host "  ✅ Ollama (port 11434) - LISTENING" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Ollama (port 11434) - NOT LISTENING (optional)" -ForegroundColor Yellow
    }

    Write-Host ""

    if (-not $allPassed) {
        Write-Host "⛔ Pre-flight checks FAILED. Start required services first." -ForegroundColor Red
        Write-Host "   Hint: cd $ProjectRoot && docker-compose up -d" -ForegroundColor DarkGray
        exit 1
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 5. VERIFY ZERO TRUST CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "🔐 Verifying Zero Trust configuration..." -ForegroundColor Yellow

$verifyResult = poetry run python -c @"
import os
import sys
os.environ.setdefault('OMEGA_ENV', 'stable')
try:
    from omega_kg.settings import settings
    checks = [
        settings.postgres_db == 'omega_kg_stable',
        settings.postgres_port == 5433,
        settings.app_port == 8002,
    ]
    if all(checks):
        print('PASS')
        sys.exit(0)
    else:
        print(f'FAIL: DB={settings.postgres_db}, PG_PORT={settings.postgres_port}, APP_PORT={settings.app_port}')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@ 2>&1

if ($verifyResult -match 'PASS') {
    Write-Host "  ✅ Settings loaded with correct STABLE configuration" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Settings verification: $verifyResult" -ForegroundColor Yellow
}
Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════════
# 6. START CAPTURE SERVER
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "🚀 Starting Omega_KG STABLE capture server on port 8002..." -ForegroundColor Magenta
Write-Host ""

$logPath = Join-Path $ProjectRoot "logs\Omega_KG_stable_server.log"
$pidPath = Join-Path $ProjectRoot "logs\Omega_KG_stable_server.pid"

# Ensure logs directory exists
$logsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

if ($BackgroundMode) {
    # Background mode - start server as job
    $serverJob = Start-Job -ScriptBlock {
        param($root)
        Set-Location $root
        poetry run omega-kg serve 2>&1
    } -ArgumentList $ProjectRoot

    $serverJob.Id | Out-File -FilePath $pidPath -Force
    Write-Host "  └─ Server started in background (Job ID: $($serverJob.Id))" -ForegroundColor DarkGray
    Write-Host "     Log: $logPath" -ForegroundColor DarkGray
    Write-Host "     Stop with: Stop-Job -Id $($serverJob.Id)" -ForegroundColor DarkGray
} else {
    # Foreground mode - interactive
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host " STABLE Server Starting (Ctrl+C to stop)" -ForegroundColor Magenta
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    poetry run omega-kg serve 2>&1 | Tee-Object -FilePath $logPath
}
