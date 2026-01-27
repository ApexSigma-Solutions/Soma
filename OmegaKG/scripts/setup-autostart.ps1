#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Configure Windows Task Scheduler to start Omega KG server at login
.DESCRIPTION
    Creates a scheduled task that launches the Omega KG capture server
    in a separate window when you log in.
#>

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$ProjectRoot = (Split-Path -Parent $PSScriptRoot)

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Omega KG - Auto-Start Configuration                     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Task details
$TaskName = "Omega_KG_CaptureServer"
$TaskDescription = "Starts Omega KG Capture Server at login"

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "⚠️  Task '$TaskName' already exists" -ForegroundColor Yellow
    $Response = Read-Host "Do you want to replace it? (y/n)"
    if ($Response -ne 'y') {
        Write-Host "Setup cancelled" -ForegroundColor Gray
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✓ Removed existing task" -ForegroundColor Green
}

# Create startup script wrapper
$StartupScriptPath = Join-Path $ProjectRoot "start-full-stack-persistent.ps1"
@"
#!/usr/bin/env pwsh
# Auto-generated startup script for Task Scheduler
`$ErrorActionPreference = "Stop"

# Set window title
`$host.UI.RawUI.WindowTitle = "Omega KG Full Stack (Persistent)"

# Change to project directory
Set-Location "$ProjectRoot"

Write-Host "🚀 Launching Omega KG Full Stack in Persistent Mode..." -ForegroundColor Cyan
& (Join-Path "$ProjectRoot" "scripts\start_full_stack.ps1") -Persistent -ShowConsole
"@ | Set-Content $StartupScriptPath -Encoding UTF8

Write-Host "✓ Created startup script: $StartupScriptPath" -ForegroundColor Green

# Create the scheduled task action
$Action = New-ScheduledTaskAction `
    -Execute "pwsh.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Normal -File `"$StartupScriptPath`"" `
    -WorkingDirectory $ProjectRoot

# Create the trigger (at logon)
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Create the principal (run as current user, highest privileges)
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Register the task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Description $TaskDescription `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Host "✓ Task '$TaskName' created successfully" -ForegroundColor Green
Write-Host ""

# Show task details
Write-Host "Task Configuration:" -ForegroundColor Cyan
Write-Host "  Name:        $TaskName"
Write-Host "  Trigger:     At logon (user: $env:USERNAME)"
Write-Host "  Action:      Start Omega KG server in new window"
Write-Host "  Script:      $StartupScriptPath"
Write-Host "  Auto-Retry:  Yes (3 attempts, 1 minute interval)"
Write-Host ""

# Options
Write-Host "What would you like to do?" -ForegroundColor Yellow
Write-Host "  1. Test the task now (start server)"
Write-Host "  2. Disable auto-start (keep task but disable)"
Write-Host "  3. Remove auto-start completely"
Write-Host "  4. Do nothing (task is ready for next login)"
Write-Host ""

$Choice = Read-Host "Enter choice (1-4)"

switch ($Choice) {
    "1" {
        Write-Host ""
        Write-Host "🚀 Starting task now..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✓ Task started! Check the new window." -ForegroundColor Green
        Write-Host "   (The server window should appear in a moment)" -ForegroundColor Gray
    }
    "2" {
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
        Write-Host "✓ Auto-start disabled (task still exists)" -ForegroundColor Yellow
        Write-Host "   To re-enable: Enable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    }
    "3" {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Remove-Item $StartupScriptPath -Force -ErrorAction SilentlyContinue
        Write-Host "✓ Auto-start removed completely" -ForegroundColor Green
    }
    default {
        Write-Host "✓ Configuration complete!" -ForegroundColor Green
        Write-Host "   Server will auto-start at next login" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  Start now:     Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Stop:          Stop-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Disable:       Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Enable:        Enable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Remove:        Unregister-ScheduledTask -TaskName '$TaskName'"
Write-Host "  View status:   Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
