# =============================================================================
# InGest-LLM.as Service Restart Script
# =============================================================================
# Purpose: Gracefully stop and restart the InGest-LLM.as service
# Usage: .\restart_ingest_llm.ps1 [-ShowConsole]
# =============================================================================

param (
    [switch]$ShowConsole
)

$ErrorActionPreference = "Stop"

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "InGest-LLM.as Service Restart" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# --- 1. STOP EXISTING PROCESSES ---
Write-Host "Stopping existing InGest-LLM processes..." -ForegroundColor Yellow

# Find and stop Uvicorn processes
$UvicornProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*ingest_llm_as*"
}

if ($UvicornProcs) {
    foreach ($proc in $UvicornProcs) {
        Write-Host "  [→] Stopping Uvicorn (PID: $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  [✓] Uvicorn stopped" -ForegroundColor Green
} else {
    Write-Host "  [i] No Uvicorn processes found" -ForegroundColor Gray
}

# Find and stop Cloudflared processes
$CloudflaredProcs = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*valhalla-gateway*"
}

if ($CloudflaredProcs) {
    foreach ($proc in $CloudflaredProcs) {
        Write-Host "  [→] Stopping Cloudflared (PID: $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  [✓] Cloudflared stopped" -ForegroundColor Green
} else {
    Write-Host "  [i] No Cloudflared processes found" -ForegroundColor Gray
}

# Wait for processes to fully terminate
Start-Sleep -Seconds 2

Write-Host ""

# --- 2. START SERVICES ---
Write-Host "Starting InGest-LLM services..." -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StartScript = Join-Path $ProjectRoot "scripts\start_ingest_llm.ps1"

if (Test-Path $StartScript) {
    $StartArgs = @{
        FilePath = "powershell.exe"
        ArgumentList = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`" $(if ($ShowConsole) {'-ShowConsole'} else {''})"
        WindowStyle = "Normal"
        PassThru = $true
        WorkingDirectory = $ProjectRoot
    }
    
    $Launcher = Start-Process @StartArgs
    Write-Host "  [✓] Launcher started (PID: $($Launcher.Id))" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 8 seconds for services to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 8
    
    # Verify services are running
    $UvicornCheck = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*uvicorn*ingest_llm_as*"
    }
    
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host "Service Status" -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Cyan
    
    if ($UvicornCheck) {
        Write-Host "  ✅ Uvicorn API:    http://localhost:8766 (PID: $($UvicornCheck.Id))" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Uvicorn API:    Not running" -ForegroundColor Red
        Write-Host "  [!] Check logs in: $ProjectRoot\logs\" -ForegroundColor Yellow
    }
    
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host ""
    
} else {
    Write-Error "Start script not found: $StartScript"
}
