#!/usr/bin/env pwsh
#Requires -Version 5.1

<#
.SYNOPSIS
    Fix Soma Ecosystem Desktop Shortcut
.DESCRIPTION
    Removes any existing shortcuts and creates a properly configured new one
    that will show a window and execute correctly.
#>

$ErrorActionPreference = "Stop"

Write-Host "Soma Ecosystem - Desktop Shortcut Fixer" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ShortcutName = "Soma Ecosystem"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ProjectRoot = $PSScriptRoot
$BatchFile = Join-Path $ProjectRoot "Start-Soma-Debug.bat"

# Check if batch file exists
if (-not (Test-Path $BatchFile)) {
    Write-Host "[ERROR] Batch file not found: $BatchFile" -ForegroundColor Red
    Write-Host "Make sure you're running this from the Soma project directory." -ForegroundColor Yellow
    exit 1
}

Write-Host "Project root: $ProjectRoot" -ForegroundColor Gray
Write-Host "Batch file: $BatchFile" -ForegroundColor Gray
Write-Host "Desktop path: $DesktopPath" -ForegroundColor Gray
Write-Host ""

# Remove existing shortcuts
$existingShortcuts = @(
    (Join-Path $DesktopPath "$ShortcutName.lnk"),
    (Join-Path $DesktopPath "Start-Soma.lnk"),
    (Join-Path $DesktopPath "Soma.lnk")
)

foreach ($shortcut in $existingShortcuts) {
    if (Test-Path $shortcut) {
        Write-Host "Removing existing shortcut: $shortcut" -ForegroundColor Yellow
        Remove-Item $shortcut -Force
    }
}

# Create new shortcut
Write-Host "Creating new desktop shortcut..." -ForegroundColor Cyan

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "$ShortcutName.lnk"))
    
    # Use the debug batch file for now to see what's happening
    $Shortcut.TargetPath = $BatchFile
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "Launch Soma Biomorphic Ecosystem (Debug Mode)"
    $Shortcut.IconLocation = "powershell.exe,0"
    
    # CRITICAL: WindowStyle = 1 (Normal window) not 7 (Minimized)
    # This ensures the window is visible
    $Shortcut.WindowStyle = 1
    
    # Save
    $Shortcut.Save()
    
    Write-Host ""
    Write-Host "✓ Desktop shortcut created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Shortcut Details:" -ForegroundColor Cyan
    Write-Host "  Name: $ShortcutName" -ForegroundColor White
    Write-Host "  Location: $DesktopPath\$ShortcutName.lnk" -ForegroundColor White
    Write-Host "  Target: $($Shortcut.TargetPath)" -ForegroundColor White
    Write-Host "  Working Directory: $($Shortcut.WorkingDirectory)" -ForegroundColor White
    Write-Host "  Window Style: Normal (visible)" -ForegroundColor White
    Write-Host ""
    Write-Host "Double-click the '$ShortcutName' icon on your desktop to start." -ForegroundColor Green
    Write-Host "A window will appear showing the startup progress." -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host "[ERROR] Failed to create shortcut: $_" -ForegroundColor Red
    Write-Host "Stack Trace: $($_.ScriptStackTrace)" -ForegroundColor DarkGray
    exit 1
}
