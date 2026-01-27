# Restart Omega_KG Capture Server
# This will restart the capture server to load the new auth routes

Write-Host "Stopping Omega_KG capture server..." -ForegroundColor Yellow

# Find and stop the capture server process
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*capture_server*"
} | Stop-Process -Force

Start-Sleep -Seconds 2

Write-Host "Starting Omega_KG capture server..." -ForegroundColor Green

# Start the capture server
cd Omega_KG_stable
poetry run python -m omega_kg.capture_server

Write-Host "Capture server restarted!" -ForegroundColor Green
