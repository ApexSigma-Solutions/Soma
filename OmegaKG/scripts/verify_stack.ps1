# Omega Stack Verification Protocol
# ---------------------------------
$ErrorActionPreference = "SilentlyContinue"

Write-Host "`n🔍 OMEGA FORENSIC SCAN INITIATED..." -ForegroundColor Cyan

# 1. Check for the Processes
$pPython   = Get-Process -Name "python" | Where-Object { $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*8765*" }
$pHookdeck = Get-Process -Name "hookdeck"

Write-Host "`n1. PROCESS STATUS:" -ForegroundColor Yellow
if ($pPython) { 
    Write-Host "   [✔] Capture Server (PID: $($pPython.Id)) is MEMORY RESIDENT." -ForegroundColor Green 
} else { 
    Write-Host "   [X] Capture Server is DEAD/NOT FOUND." -ForegroundColor Red 
}

if ($pHookdeck) { 
    Write-Host "   [✔] Hookdeck CLI (PID: $($pHookdeck.Id)) is MEMORY RESIDENT." -ForegroundColor Green 
} else { 
    Write-Host "   [X] Hookdeck CLI is DEAD/NOT FOUND." -ForegroundColor Red 
}

# 2. Check the Ports (The "Truth Serum")
Write-Host "`n2. PORT STATUS (8765):" -ForegroundColor Yellow
$portCheck = Get-NetTCPConnection -LocalPort 8765
if ($portCheck.State -eq "Listen") {
    Write-Host "   [✔] Port 8765 is LISTENING (Owned by PID $($portCheck.OwningProcess))." -ForegroundColor Green
} else {
    Write-Host "   [X] Port 8765 is CLOSED." -ForegroundColor Red
}

# 3. Functional Health Check
Write-Host "`n3. API HEALTH PING:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8765/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   [✔] API Responded: $($response)" -ForegroundColor Green
} catch {
    Write-Host "   [X] API Unreachable: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Environment Sanity Check (Why Task Scheduler fails)
Write-Host "`n4. CONTEXT CHECK:" -ForegroundColor Yellow
if ($env:HOOKDECK_API_KEY) {
    Write-Host "   [✔] HOOKDECK_API_KEY is present in this session." -ForegroundColor Green
} else {
    Write-Host "   [!] HOOKDECK_API_KEY is MISSING. (CLI usually hangs waiting for browser login without this)." -ForegroundColor Magenta
}

Write-Host "`n---------------------------------"
Write-Host "DIAGNOSIS COMPLETE" -ForegroundColor Cyan