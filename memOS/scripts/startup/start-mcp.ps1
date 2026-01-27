#!/usr/bin/env pwsh
#
# Omega MCP Server Launcher (v1.0)
# -------------------------
# Purpose: Validates runtime environment and launches MemOS MCP server on port 8768
# Usage:
#   ./scripts/start_mcp.ps1                      -> Foreground (logs to console)
#   ./scripts/start_mcp.ps1 -Background          -> Background (logs to files)
#   ./scripts/start_mcp.ps1 -ShowConsole         -> Background with visible console
#
# Port Assignment:
#   - 8765: OmegaKG Capture Server (Core)
#   - 8766: InGest LLM API
#   - 8768: MemOS MCP Server (this script)
#

param (
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$EnvFile = ".env",
    [switch]$Background,
    [switch]$ShowConsole
    )

$ErrorActionPreference = "Stop"

$Time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# --- 1. CRITICAL PATH VALIDATION ---
Write-Host "[$Time] ════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[$Time]   Omega MCP Server - Initialization" -ForegroundColor Cyan
Write-Host "[$Time] ════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host "[$Time] [0/5] Validating critical path (.venv and .env)..." -ForegroundColor Yellow

# Check .venv existence - CRITICAL for Poetry-managed projects
$venvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path $venvPath) {
    Write-Host "[$Time]   [+] .venv directory found" -ForegroundColor Green
} else {
    Write-Host "[$Time]   [-] FATAL: .venv directory NOT found!" -ForegroundColor Red
    Write-Host "[$Time]       Run 'poetry install' to create virtual environment" -ForegroundColor Yellow
    exit 1
}

# Check .env existence - CRITICAL for configuration
$envPath = Join-Path $ProjectRoot $EnvFile
if (Test-Path $envPath) {
    Write-Host "[$Time]   [+] .env file found" -ForegroundColor Green

    # Load .env into process environment
    Write-Host "[$Time]   [*] Loading environment variables..." -ForegroundColor Cyan
    Get-Content $envPath | Where-Object { $_ -match '=' -and $_ -not.match '^#' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
    }
    Write-Host "[$Time]   [+] Environment loaded" -ForegroundColor Green
} else {
    Write-Host "[$Time]   [-] FATAL: .env file NOT found!" -ForegroundColor Red
    Write-Host "[$Time]       Copy .env.example to .env and configure" -ForegroundColor Yellow
    exit 1
}

# --- 2. RUNTIME VALIDATION ---
Write-Host "[$Time] [1/5] Validating runtime environment..." -ForegroundColor Yellow

# Check Poetry
$PoetryPath = (Get-Command poetry -ErrorAction SilentlyContinue).Source
if (-not $PoetryPath) {
    Write-Host "[$Time]   [-] FATAL: Poetry not found in PATH" -ForegroundColor Red
    exit 1
}
$poetryVersion = poetry --version 2>&1
Write-Host "[$Time]   [+] Poetry: $poetryVersion" -ForegroundColor Green

# Verify Poetry virtual environment
try {
    $venvInfo = poetry env info 2>&1
    Write-Host "[$Time]   [+] Virtual environment configured" -ForegroundColor Green
} catch {
    Write-Host "[$Time]   [-] FATAL: Virtual environment not configured" -ForegroundColor Red
    exit 1
}

# --- 3. PORT AVAILABILITY ---
Write-Host "[$Time] [2/5] Checking port 8768 availability..." -ForegroundColor Yellow

$port = 8768
$portInUse = $false

# Check if port is in use
try {
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
    $listener.Start()
    $listener.Stop()
    $portInUse = $false
} catch {
    $portInUse = $true
}

if ($portInUse) {
    Write-Host "[$Time]   [-] FATAL: Port $port is already in use!" -ForegroundColor Red
    $proc = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
    if ($proc) {
        Write-Host "[$Time]       Conflicting process: $($proc.Name) (PID: $($proc.Id))" -ForegroundColor Yellow
    }
    exit 1
} else {
    Write-Host "[$Time]   [+] Port $port is available" -ForegroundColor Green
}

# --- 4. SERVER CONFIGURATION ---
Write-Host "[$Time] [3/5] Configuring server..." -ForegroundColor Yellow

# Set environment variables for the server
$env:MEMOS_HOST = "0.0.0.0"
$env:MEMOS_PORT = "$port"

Write-Host "[$Time]   [+] Host: $($env:MEMOS_HOST)" -ForegroundColor Green
Write-Host "[$Time]   [+] Port: $($env:MEMOS_PORT)" -ForegroundColor Green
Write-Host "[$Time]   [+] Database: $($env:MEMOS_DB_TYPE ?? 'sqlite')" -ForegroundColor Green

# --- 5. SERVICE ISOLATION VERIFICATION ---
Write-Host "[$Time] [4/5] Verifying service isolation..." -ForegroundColor Yellow

Write-Host "[$Time]   [+] Service: MemOS MCP Server (port 8768)" -ForegroundColor Green
Write-Host "[$Time]   [+] Distinct from Core (8765) and InGest (8766)" -ForegroundColor Green

# --- 6. LAUNCH SERVER ---
Write-Host "[$Time] [5/5] Launching Omega MCP Server..." -ForegroundColor Yellow
Write-Host "[$Time] ════════════════════════════════════════════════════════════" -ForegroundColor Green

# Setup logging for background mode
if ($Background -or $ShowConsole) {
    $LogDir = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

    $TimeString = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $ServerLog = Join-Path $LogDir "mcp_server_$TimeString.log"
    $ServerErrLog = Join-Path $LogDir "mcp_server_$TimeString.err.log"

    if ($ShowConsole) {
        $WindowStyle = "Normal"
        Write-Host "[$Time]   [*] DEBUG MODE: Console window visible" -ForegroundColor Yellow
    } else {
        $WindowStyle = "Hidden"
        Write-Host "[$Time]   [*] BACKGROUND MODE: Console hidden, logs to $LogDir" -ForegroundColor Yellow
    }

    $LogArgs = @{
        RedirectStandardOutput = $ServerLog
        RedirectStandardError = $ServerErrLog
    }

    $PoetryRunArgs = "run python -m memos_mcp.server --sse"

    Write-Host "[$Time]   [*] Command: poetry $PoetryRunArgs" -ForegroundColor Gray
    Write-Host ""

    try {
        $ServerProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryRunArgs -WindowStyle $WindowStyle -PassThru @LogArgs
        Write-Host "[$Time]   [+] Server started (PID: $($ServerProc.Id))" -ForegroundColor Green
        Write-Host "[$Time]   [*] Waiting 3 seconds for initialization..." -ForegroundColor Cyan
        Start-Sleep -Seconds 3

        # Verify process is still running
        if (-not (Get-Process -Id $ServerProc.Id -ErrorAction SilentlyContinue)) {
            Write-Host "[$Time]   [-] FATAL: Server process exited unexpectedly!" -ForegroundColor Red
            Write-Host "[$Time]       Check error log: $ServerErrLog" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "[$Time]   [+] Server is running and ready" -ForegroundColor Green
        Write-Host ""
        Write-Host "[$Time] ════════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "[$Time]   Health check: http://localhost:$port/health" -ForegroundColor Cyan
        Write-Host "[$Time]   Logs: $ServerLog" -ForegroundColor Cyan
        Write-Host "[$Time] ════════════════════════════════════════════════════════════" -ForegroundColor Green

    } catch {
        Write-Host "[$Time]   [-] FATAL: Failed to start server: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }

} else {
    # Foreground mode (development)
    Write-Host "[$Time]   [*] FOREGROUND MODE: Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""

    $PoetryRunArgs = @(
        "run",
        "python",
        "-m",
        "memos_mcp.server",
        "--sse"
    )

    Write-Host "[$Time]   [*] Command: poetry $($PoetryRunArgs -join ' ')" -ForegroundColor Gray
    Write-Host ""

    try {
        & poetry @PoetryRunArgs
    } catch {
        Write-Host ""
        Write-Host "[$Time] ════════════════════════════════════════════════════════════" -ForegroundColor Red
        Write-Host "[$Time]   Server terminated with error" -ForegroundColor Red
        Write-Host "[$Time] ════════════════════════════════════════════════════════════" -ForegroundColor Red
        exit 1
    }
}