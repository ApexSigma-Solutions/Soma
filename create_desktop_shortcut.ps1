<#
.SYNOPSIS
    Creates a desktop shortcut for starting the Soma Ecosystem
    
.DESCRIPTION
    Generates a .lnk shortcut on the user's desktop that launches start_ecosystem.ps1
    with proper execution policy and working directory settings.
    
.EXAMPLE
    .\create_desktop_shortcut.ps1
#>

param(
    [switch]$Persistent,
    [switch]$ShowConsole
)

$ErrorActionPreference = 'Stop'

# Get paths
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Join-Path $ScriptRoot "start_ecosystem.ps1"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Start Soma Ecosystem.lnk"

Write-Host "Creating desktop shortcut..." -ForegroundColor Cyan

# Verify start_ecosystem.ps1 exists
if (-not (Test-Path $StartScript)) {
    Write-Host "Error: start_ecosystem.ps1 not found at $StartScript" -ForegroundColor Red
    exit 1
}

# Build arguments
$Arguments = "-ExecutionPolicy Bypass -NoExit -File `"$StartScript`""
if ($Persistent) {
    $Arguments += " -Persistent"
}
if ($ShowConsole) {
    $Arguments += " -ShowConsole"
}

try {
    # Create WScript Shell COM object
    $WshShell = New-Object -ComObject WScript.Shell
    
    # Create shortcut
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = $Arguments
    $Shortcut.WorkingDirectory = $ScriptRoot
    $Shortcut.Description = "Launch Soma Biomorphic Knowledge Ecosystem"
    $Shortcut.IconLocation = "powershell.exe,0"
    $Shortcut.WindowStyle = 1  # Normal window
    $Shortcut.Save()
    
    Write-Host "Shortcut created successfully!" -ForegroundColor Green
    Write-Host "  Location: $ShortcutPath" -ForegroundColor White
    Write-Host "  Target: PowerShell" -ForegroundColor White
    Write-Host "  Script: $StartScript" -ForegroundColor White
    
    if ($Persistent) {
        Write-Host "  Mode: Persistent (with watchdog)" -ForegroundColor Yellow
    }
    if ($ShowConsole) {
        Write-Host "  Console: Visible (debug mode)" -ForegroundColor Yellow
    }
    
    Write-Host "`nYou can now double-click 'Start Soma Ecosystem' on your desktop!" -ForegroundColor Cyan
}
catch {
    Write-Host "Error creating shortcut: $_" -ForegroundColor Red
    exit 1
}
