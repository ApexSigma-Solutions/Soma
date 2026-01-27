
function Test-Endpoint {
    param($Url, $Name)
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host " [OK] $Name" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host " [DOWN] $Name ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
    return $false
}

Clear-Host
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   OmegaKG Ecosystem Monitor" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

while ($true) {
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "`n[$time] Health Check:" -ForegroundColor Gray

    $backend = Test-Endpoint "http://localhost:8765/health" "Backend (OmegaKG)"
    $frontend = Test-Endpoint "http://localhost:6001/" "Frontend (CortexBridge)"
    # memOS is a bit trickier as it's SSE, but we can check if port is open
    $memosParams = @{ ComputerName = "localhost"; Port = 8768; InformationLevel = "Quiet" }
    if (Test-NetConnection @memosParams -WarningAction SilentlyContinue) {
         Write-Host " [OK] memOS.MCP (Port 8768 Open)" -ForegroundColor Green
    } else {
         Write-Host " [DOWN] memOS.MCP" -ForegroundColor Red
    }

    $ingest = Test-Endpoint "http://localhost:8766/health" "InGest-LLM"

    Write-Host "`n---------------------------------------------"
    Write-Host "Press Ctrl+C to stop monitoring."
    
    Start-Sleep -Seconds 5
    # Move cursor up to overwrite previous output for a dashboard effect
    # (Simple scroll implementation for now)
}
