#!/usr/bin/env pwsh
#Requires -Version 5.1

<#
.SYNOPSIS
    Diagnostic script for Soma Ecosystem startup issues
.DESCRIPTION
    Checks PowerShell availability and provides troubleshooting guidance
#>

Write-Host "Soma Ecosystem - Startup Diagnostics" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check PowerShell version
Write-Host "PowerShell Version Check:" -ForegroundColor Yellow
Write-Host "  Current Process: $($PSVersionTable.PSVersion)" -ForegroundColor White
Write-Host "  Edition: $($PSVersionTable.PSEdition)" -ForegroundColor White
Write-Host ""

# Check for PowerShell 7
Write-Host "PowerShell 7 Detection:" -ForegroundColor Yellow

$pwshPaths = @(
    "pwsh",
    "C:\Program Files\PowerShell\7\pwsh.exe",
    "C:\Program Files\PowerShell\7-preview\pwsh.exe",
    "$env:USERPROFILE\.dotnet\tools\pwsh.exe"
)

$foundPwsh = $false
foreach ($path in $pwshPaths) {
    try {
        if ($path -eq "pwsh") {
            $cmd = Get-Command "pwsh" -ErrorAction SilentlyContinue
            if ($cmd) {
                Write-Host "  ✓ Found in PATH: $($cmd.Source)" -ForegroundColor Green
                $foundPwsh = $true
                
                # Get version
                try {
                    $version = & $cmd.Source --version 2>$null
                    Write-Host "    Version: $version" -ForegroundColor Gray
                } catch {}
            }
        } elseif (Test-Path $path) {
            Write-Host "  ✓ Found at: $path" -ForegroundColor Green
            $foundPwsh = $true
            
            # Get version
            try {
                $version = & $path --version 2>$null
                Write-Host "    Version: $version" -ForegroundColor Gray
            } catch {}
        }
    } catch {
        Write-Host "  ✗ Not found: $path" -ForegroundColor Red
    }
}

if (-not $foundPwsh) {
    Write-Host "  ✗ PowerShell 7 not found" -ForegroundColor Red
}

Write-Host ""

# Check for Windows PowerShell
Write-Host "Windows PowerShell Detection:" -ForegroundColor Yellow

$winPsPaths = @(
    "powershell",
    "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe",
    "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)

$foundWinPs = $false
foreach ($path in $winPsPaths) {
    try {
        if ($path -eq "powershell") {
            $cmd = Get-Command "powershell" -ErrorAction SilentlyContinue
            if ($cmd) {
                Write-Host "  ✓ Found in PATH: $($cmd.Source)" -ForegroundColor Green
                $foundWinPs = $true
            }
        } elseif (Test-Path $path) {
            Write-Host "  ✓ Found at: $path" -ForegroundColor Green
            $foundWinPs = $true
        }
    } catch {
        Write-Host "  ✗ Not found: $path" -ForegroundColor Red
    }
}

if (-not $foundWinPs) {
    Write-Host "  ✗ Windows PowerShell not found" -ForegroundColor Red
}

Write-Host ""

# Environment check
Write-Host "Environment Check:" -ForegroundColor Yellow
Write-Host "  PATH entries:" -ForegroundColor White
$env:PATH -split ";" | ForEach-Object {
    if ($_ -match "PowerShell|powershell") {
        Write-Host "    $_" -ForegroundColor Green
    }
}

Write-Host ""

# Recommendations
Write-Host "Recommendations:" -ForegroundColor Yellow

if ($foundPwsh) {
    Write-Host "  ✓ PowerShell 7 is available - you're good to go!" -ForegroundColor Green
    Write-Host "" -ForegroundColor White
    Write-Host "  To fix the desktop shortcut, try:" -ForegroundColor Cyan
    Write-Host "  1. Delete the existing 'Soma Ecosystem' shortcut from your desktop" -ForegroundColor White
    Write-Host "  2. Run: .\Create-DesktopShortcut.ps1" -ForegroundColor White
    Write-Host "  3. Double-click the new shortcut" -ForegroundColor White
} elseif ($foundWinPs) {
    Write-Host "  ⚠ Only Windows PowerShell found (PowerShell 5)" -ForegroundColor Yellow
    Write-Host "  The batch file should still work, but PowerShell 7 is recommended" -ForegroundColor Yellow
    Write-Host "" -ForegroundColor White
    Write-Host "  To install PowerShell 7:" -ForegroundColor Cyan
    Write-Host "  winget install Microsoft.PowerShell" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "  Or download from:" -ForegroundColor Cyan
    Write-Host "  https://github.com/PowerShell/PowerShell/releases" -ForegroundColor White
} else {
    Write-Host "  ✗ No PowerShell found - installation required" -ForegroundColor Red
    Write-Host "" -ForegroundColor White
    Write-Host "  Install PowerShell 7:" -ForegroundColor Cyan
    Write-Host "  1. winget install Microsoft.PowerShell" -ForegroundColor White
    Write-Host "  2. Or download MSI from GitHub releases" -ForegroundColor White
    Write-Host "  3. Restart your computer after installation" -ForegroundColor White
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
