# Cleanup script - Kill any existing capture server processes
Write-Host "=== Cleaning up existing processes ===" -ForegroundColor Cyan

# Kill any existing Poetry processes running capture server
try {
    $processes = Get-Process -Name "poetry" -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "Found Poetry processes:" -ForegroundColor Yellow
        foreach ($proc in $processes) {
            Write-Host "  Killing PID: $($proc.Id)" -ForegroundColor Red
            $proc.Kill()
            $proc.WaitForExit(5000)
        }
    } else {
        Write-Host "No Poetry processes found" -ForegroundColor Green
    }
} catch {
    Write-Host "Error killing Poetry processes: $($_.Exception.Message)" -ForegroundColor Red
}

# Kill any existing node processes (Hookdeck)
try {
    $processes = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*hookdeck*" }
    if ($processes) {
        Write-Host "Found Hookdeck node processes:" -ForegroundColor Yellow
        foreach ($proc in $processes) {
            Write-Host "  Killing PID: $($proc.Id)" -ForegroundColor Red
            $proc.Kill()
            $proc.WaitForExit(5000)
        }
    } else {
        Write-Host "No Hookdeck processes found" -ForegroundColor Green
    }
} catch {
    Write-Host "Error killing node processes: $($_.Exception.Message)" -ForegroundColor Red
}

# Wait a moment for ports to be released
Start-Sleep -Seconds 2

Write-Host "`nCleanup complete!" -ForegroundColor Green
Write-Host "You can now run start_full_stack.ps1" -ForegroundColor Cyan
