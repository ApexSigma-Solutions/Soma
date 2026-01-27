# =============================================================================
# Complete InGest-LLM Cleanup and Restart Script
# =============================================================================
# Purpose: Clean up all InGest-LLM processes and restart fresh
# =============================================================================

param (
    [switch]$ShowConsole,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "InGest-LLM Complete Cleanup and Restart" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# --- 1. KILL ALL PYTHON PROCESSES RELATED TO INGEST-LLM ---
Write-Host "Step 1: Cleaning up all InGest-LLM processes..." -ForegroundColor Yellow

$IngestProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $cmdLine -like "*ingest_llm*" -or $cmdLine -like "*uvicorn*" -and $cmdLine -like "*8766*"
    } catch {
        $false
    }
}

if ($IngestProcesses) {
    Write-Host "  Found $($IngestProcesses.Count) InGest-LLM related processes" -ForegroundColor Yellow
    foreach ($proc in $IngestProcesses) {
        try {
            Write-Host "    [→] Stopping PID: $($proc.Id)..." -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "    [!] Could not stop PID: $($proc.Id)" -ForegroundColor Red
        }
    }
    Write-Host "  [✓] Cleanup complete" -ForegroundColor Green
} else {
    Write-Host "  [i] No InGest-LLM processes found" -ForegroundColor Gray
}

# --- 2. WAIT FOR PORT TO BE FREE ---
Write-Host "`nStep 2: Waiting for port 8766 to be released..." -ForegroundColor Yellow
$maxWait = 10
$waited = 0

while ($waited -lt $maxWait) {
    $portInUse = Get-NetTCPConnection -LocalPort 8766 -ErrorAction SilentlyContinue
    if (-not $portInUse) {
        Write-Host "  [✓] Port 8766 is free" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
    $waited++
    Write-Host "    Waiting... ($waited/$maxWait)" -ForegroundColor Gray
}

if ($waited -ge $maxWait) {
    Write-Host "  [!] Port 8766 still in use after ${maxWait}s" -ForegroundColor Red
    if (-not $Force) {
        Write-Host "  [!] Use -Force to continue anyway" -ForegroundColor Yellow
        exit 1
    }
}

# --- 3. RUN BOOTSTRAP ---
Write-Host "`nStep 3: Running NLP dependency bootstrap..." -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BootstrapScript = Join-Path $ProjectRoot "bootstrap.py"

if (Test-Path $BootstrapScript) {
    try {
        Push-Location $ProjectRoot
        $BootstrapResult = & poetry run python bootstrap.py
        Pop-Location
        Write-Host "  [✓] Bootstrap complete" -ForegroundColor Green
    } catch {
        Pop-Location
        Write-Host "  [⚠️] Bootstrap failed: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  [i] Continuing anyway..." -ForegroundColor Gray
    }
} else {
    Write-Host "  [i] Bootstrap script not found - skipping" -ForegroundColor Gray
}

# --- 4. START FRESH SERVICE ---
Write-Host "`nStep 4: Starting fresh InGest-LLM service..." -ForegroundColor Cyan

$StartScript = Join-Path $ProjectRoot "scripts\start_ingest_llm.ps1"

if (Test-Path $StartScript) {
    try {
        Push-Location $ProjectRoot
        
        # Start the service
        $StartArgs = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$StartScript`""
        )
        
        if ($ShowConsole) {
            $StartArgs += "-ShowConsole"
        }
        
        $LauncherProc = Start-Process -FilePath "powershell.exe" `
            -ArgumentList ($StartArgs -join " ") `
            -WindowStyle Normal `
            -PassThru `
            -WorkingDirectory $ProjectRoot
        
        Pop-Location
        
        Write-Host "  [✓] Service launcher started (PID: $($LauncherProc.Id))" -ForegroundColor Green
        Write-Host "`nWaiting 10 seconds for service initialization..." -ForegroundColor Gray
        Start-Sleep -Seconds 10
        
        # --- 5. VERIFY SERVICE ---
        Write-Host "`nStep 5: Verifying service..." -ForegroundColor Cyan
        
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8766/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "  [✓] Service is responding!" -ForegroundColor Green
                Write-Host "  [✓] Health check: $($response.Content.Substring(0, [Math]::Min(100, $response.Content.Length)))..." -ForegroundColor Green
            }
        } catch {
            Write-Host "  [❌] Service not responding: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "  [i] Check logs in: $ProjectRoot\logs\" -ForegroundColor Yellow
        }
        
    } catch {
        if (Test-Path variable:ProjectRoot) { Pop-Location }
        Write-Host "  [❌] Failed to start service: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [❌] Start script not found: $StartScript" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "✅ InGest-LLM Restart Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "Service URL: http://localhost:8766" -ForegroundColor Cyan
Write-Host "API Docs:    http://localhost:8766/docs" -ForegroundColor Cyan
Write-Host "Health:      http://localhost:8766/health" -ForegroundColor Cyan
Write-Host ""
