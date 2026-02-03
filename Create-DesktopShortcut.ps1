#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Create a desktop shortcut for Soma Ecosystem
.DESCRIPTION
    Creates a Windows desktop shortcut that launches the Soma ecosystem
    with a single double-click. Includes custom icon and working directory.
#>

[CmdletBinding()]
param(
    [string]$ProjectRoot = $PSScriptRoot,
    [string]$ShortcutName = "Soma Ecosystem",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "Creating Soma Ecosystem desktop shortcut..." -ForegroundColor Cyan

# Determine desktop path
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "$ShortcutName.lnk"

# Check if shortcut already exists
if (Test-Path $shortcutPath) {
    if (-not $Force) {
        Write-Host "Shortcut already exists at: $shortcutPath" -ForegroundColor Yellow
        $response = Read-Host "Overwrite? (Y/N)"
        if ($response -ne "Y") {
            Write-Host "Cancelled." -ForegroundColor Red
            exit 0
        }
    }
}

# Create WScript.Shell COM object
$WshShell = New-Object -ComObject WScript.Shell

# Create shortcut
$shortcut = $WshShell.CreateShortcut($shortcutPath)

# Set properties
$shortcut.TargetPath = Join-Path $ProjectRoot "Start-Soma.bat"
$shortcut.WorkingDirectory = $ProjectRoot
$shortcut.Description = "Launch Soma Biomorphic Ecosystem with Cortex Dashboard"
$shortcut.IconLocation = "powershell.exe,0"  # Default PowerShell icon (can be customized)
$shortcut.WindowStyle = 7  # Minimized window (7 = minimized, 1 = normal, 3 = maximized)

# Save shortcut
$shortcut.Save()

Write-Host "✓ Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "  Location: $shortcutPath" -ForegroundColor Gray
Write-Host "  Target: $($shortcut.TargetPath)" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "Double-click the '$ShortcutName' icon on your desktop to start the ecosystem." -ForegroundColor Cyan
