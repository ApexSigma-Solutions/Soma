# Start capture server in background

# Check if already running
$existing = Get-CimInstance Win32_Process -Filter "Name = 'uvicorn.exe'" |
    Where-Object { $_.CommandLine -match "omega_kg.capture_server" }

if ($existing) {
    Write-Host "⚠ Capture server already running (PID: $($existing.Id))"
    exit 0
}

# Start in background
$job = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    poetry run uvicorn omega_kg.capture_server:app --host 127.0.0.1 --port 8002
}

Write-Host "✓ Capture server started (Job ID: $($job.Id))"
Write-Host "  Test: http://localhost:8002/health"
Write-Host ""
Write-Host "To stop:"
Write-Host "  Stop-Job -Id $($job.Id); Remove-Job -Id $($job.Id)"
