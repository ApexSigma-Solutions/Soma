# Test Task Scheduler Integration
Write-Host "=== Checking for existing OmegaKG tasks ===" -ForegroundColor Cyan

# Get all scheduled tasks
$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -match "Omega|capture|start_full" }

if ($tasks) {
    Write-Host "`nFound existing tasks:" -ForegroundColor Green
    $tasks | ForEach-Object {
        Write-Host "  - Task: $($_.TaskName)" -ForegroundColor Yellow
        Write-Host "    State: $($_.State)" -ForegroundColor White
        Write-Host "    Path:  $($_.TaskPath)" -ForegroundColor White
    }
} else {
    Write-Host "`nNo existing OmegaKG tasks found." -ForegroundColor Yellow
}

# Check if the start_full_stack.ps1 script exists
$scriptPath = "D:\projects\OmegaKG\Omega_KG_stable\scripts\start_full_stack.ps1"
Write-Host "`n=== Checking script availability ===" -ForegroundColor Cyan
if (Test-Path $scriptPath) {
    Write-Host "Script found: $scriptPath" -ForegroundColor Green
} else {
    Write-Host "Script NOT found: $scriptPath" -ForegroundColor Red
}

# Check if we can create a simple test task
Write-Host "`n=== Task Scheduler Configuration ===" -ForegroundColor Cyan
Write-Host "Task Name: OmegaKG_StartFullStack_Test" -ForegroundColor White
Write-Host "Command: powershell.exe" -ForegroundColor White
Write-Host "Arguments: -ExecutionPolicy Bypass -File `"$scriptPath`"" -ForegroundColor White
Write-Host "Trigger: At log on" -ForegroundColor White

# Try to run the script manually (without actually creating a task)
Write-Host "`n=== Testing script execution ===" -ForegroundColor Cyan
Write-Host "Attempting to run script directly..." -ForegroundColor Yellow
try {
    & $scriptPath
    Write-Host "`nScript executed successfully!" -ForegroundColor Green
} catch {
    Write-Host "`nScript execution failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
