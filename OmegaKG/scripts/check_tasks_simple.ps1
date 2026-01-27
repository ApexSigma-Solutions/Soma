# Simple task checker
Write-Host "=== Checking OmegaKG Tasks ===" -ForegroundColor Cyan

Get-ScheduledTask | Where-Object { $_.TaskName -match "Omega" } | ForEach-Object {
    Write-Host "`nTask: $($_.TaskName)" -ForegroundColor Yellow
    Write-Host "State: $($_.State)" -ForegroundColor White
}

Write-Host "`n=== Testing Script ===" -ForegroundColor Cyan
$script = "D:\projects\OmegaKG\Omega_KG_stable\scripts\start_full_stack.ps1"
if (Test-Path $script) {
    Write-Host "Script found: $script" -ForegroundColor Green
    Write-Host "Attempting to run..." -ForegroundColor Yellow
    & $script
} else {
    Write-Host "Script NOT found!" -ForegroundColor Red
}
