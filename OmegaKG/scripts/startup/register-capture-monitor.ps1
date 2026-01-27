# Schedule Capture Server Monitor to Run at Startup
# This registers the app monitor as a Windows scheduled task

param(
    [switch]$Unregister
)

$TaskName = "Omega_KG_Capture_Monitor"
$ScriptPath = "$PSScriptRoot\task-capture-server.ps1"

function Write-Status {
    param([string]$Message, [string]$Status = "info")
    $colors = @{
        "success" = "Green"
        "error" = "Red"
        "warning" = "Yellow"
        "info" = "Cyan"
    }
    Write-Host $Message -ForegroundColor $colors[$Status]
}

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Status "❌ This script requires Administrator privileges" "error"
    Write-Host "Please run PowerShell as Administrator and try again"
    exit 1
}

if ($Unregister) {
    Write-Status "Unregistering scheduled task '$TaskName'..." "info"

    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Status "✅ Task unregistered successfully" "success"
    } catch {
        Write-Status "⚠️  Task not found or error: $_" "warning"
    }
    exit 0
}

# Verify script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Status "❌ Script not found: $ScriptPath" "error"
    exit 1
}

Write-Status "Registering scheduled task for Omega_KG Capture Monitor..." "info"

try {
    # Create the action (run PowerShell script)
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

    # Create trigger (at user logon)
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

    # Configure task settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 5)

    # Register the task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Monitors active AI web apps and starts capture-server in background when needed" `
        -Force -ErrorAction Stop | Out-Null

    Write-Status "✅ Task registered successfully!" "success"
    Write-Host "`nTask Details:"
    Write-Host "  Name: $TaskName"
    Write-Host "  Trigger: At user logon"
    Write-Host "  Script: $ScriptPath"
    Write-Host "  Status: Ready to start at next logon"

    Write-Host "`nTo verify:"
    Write-Host "  • Open Task Scheduler and look for '$TaskName' in 'Library\Omega_KG' or root"
    Write-Host "  • Or run: Get-ScheduledTask -TaskName '$TaskName' | Format-List"

    Write-Host "`nTo start the task manually:"
    Write-Host "  • Open Task Scheduler and right-click the task, select 'Run'"
    Write-Host "  • Or run: Start-ScheduledTask -TaskName '$TaskName'"

    Write-Host "`nTo remove the task:"
    Write-Host "  • Run: .\register-capture-monitor.ps1 -Unregister`n"

} catch {
    Write-Status "❌ Failed to register task: $_" "error"
    exit 1
}
