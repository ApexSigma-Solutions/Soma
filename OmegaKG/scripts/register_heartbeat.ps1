# Omega_KG Infrastructure - Heartbeat Monitor Service Registration
# Usage: Run as Administrator inside the project root
# Purpose: Registers the Python polling script as a headless Windows Service (Scheduled Task)

$TaskName = "QuipuHeartbeatMonitor"
# Relative path to the python script from project root
$ScriptRelPath = "omega_kg/quipu_ollama_heartbeat.py"

# 1. Dynamic Path Resolution
$ProjectRoot = Get-Location
$ScriptPath = Join-Path $ProjectRoot $ScriptRelPath
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "`n--- Quipu Service Registration ---" -ForegroundColor Cyan
Write-Host "Project Root : $ProjectRoot"
Write-Host "Script Path  : $ScriptPath"
Write-Host "Python Path  : $VenvPython"

# 2. Validation
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Could not find python script at: $ScriptPath"
    Write-Host "Please ensure you have created the Python file first." -ForegroundColor Yellow
    exit
}
if (-not (Test-Path $VenvPython)) {
    Write-Error "Could not find .venv python at: $VenvPython"
    Write-Host "Please ensure 'poetry install' has been run." -ForegroundColor Yellow
    exit
}

# 3. Cleanup Existing Task
Write-Host "Cleaning up old tasks..." -ForegroundColor Gray
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# 4. Create Task Definition
# IMPORTANT: WorkingDirectory is set to ProjectRoot so .env is found
$action = New-ScheduledTaskAction -Execute $VenvPython -Argument $ScriptPath -WorkingDirectory $ProjectRoot

# Trigger: Run at system startup
$trigger = New-ScheduledTaskTrigger -AtStartup

# Settings: Headless, run on battery, restart on failure
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -ExecutionTimeLimit $null -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# 5. Register Task
# Running as SYSTEM ensures it survives logouts.
# If SYSTEM cannot read your D: drive due to permissions, change User to "$env:USERNAME"
try {
    Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName $TaskName -User "SYSTEM" -RunLevel Highest -Force
    Write-Host "[SUCCESS] Task '$TaskName' registered." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to register task. Ensure you are running as Administrator." -ForegroundColor Red
    Write-Error $_
    exit
}

# 6. Start Immediately
Write-Host "Starting service..." -ForegroundColor Gray
Start-ScheduledTask -TaskName $TaskName
Write-Host "[DONE] Quipu Monitor is now running." -ForegroundColor Green
