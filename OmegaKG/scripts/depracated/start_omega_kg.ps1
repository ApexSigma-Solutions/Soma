# =============================================================================
# OmegaKG Capture Server Startup Script for Windows Task Scheduler
# =============================================================================

param(
    [switch]$NoWindow
)

# Set the working directory
Set-Location "D:\projects\OmegaKG\Omega_KG_stable"

# Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & ".venv\Scripts\Activate.ps1"
} else {
    Write-Host "WARNING: Virtual environment not found" -ForegroundColor Yellow
}

# Check if ngrok is available
$ngrokEnabled = $false
if (Test-Path ".env") {
    $envContent = Get-Content ".env" | Where-Object { $_ -match "^ENABLE_NGROK=" }
    if ($envContent -match "true") {
        $ngrokEnabled = $true
        Write-Host "Ngrok tunnel is enabled" -ForegroundColor Cyan
        Write-Host "Make sure ngrok CLI is installed and in PATH" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OmegaKG Capture Server Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: http://localhost:8765" -ForegroundColor Green
Write-Host "Health check: http://localhost:8765/health" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8765/docs" -ForegroundColor Green
Write-Host ""

if ($ngrokEnabled) {
    Write-Host "Ngrok: ENABLED (for Linear webhooks)" -ForegroundColor Yellow
    Write-Host "Webhook URL will be logged when ngrok starts" -ForegroundColor Yellow
} else {
    Write-Host "Ngrok: DISABLED" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Start the server
try {
    & python -m omega_kg.capture_server
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start capture server" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if (-not $NoWindow) {
        Read-Host "Press Enter to exit"
    }
    exit 1
}
