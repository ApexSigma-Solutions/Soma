<#
.SYNOPSIS
    Adds Poetry to Windows PATH permanently
    
.DESCRIPTION
    Adds the Poetry Scripts directory to your system PATH so it's available globally.
    This fixes the "poetry not found" error.
#>

$ErrorActionPreference = 'Stop'

$PoetryPath = "C:\Users\$env:USERNAME\AppData\Roaming\Python\Python312\Scripts"

Write-Host "Checking Poetry installation..." -ForegroundColor Cyan

# Verify Poetry exists
if (-not (Test-Path "$PoetryPath\poetry.exe")) {
    Write-Host "Error: Poetry not found at $PoetryPath" -ForegroundColor Red
    Write-Host "Please install Poetry first: https://python-poetry.org/docs/#installation" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found Poetry at: $PoetryPath" -ForegroundColor Green

# Get current user PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")

# Check if already in PATH
if ($CurrentPath -like "*$PoetryPath*") {
    Write-Host "`nPoetry is already in your PATH!" -ForegroundColor Green
    Write-Host "Close and reopen PowerShell for changes to take effect." -ForegroundColor Yellow
    exit 0
}

# Add to PATH
Write-Host "`nAdding Poetry to your PATH..." -ForegroundColor Yellow

try {
    $NewPath = "$CurrentPath;$PoetryPath"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    
    Write-Host "`nSUCCESS! Poetry has been added to your PATH." -ForegroundColor Green
    Write-Host "`nIMPORTANT: Close and reopen PowerShell for changes to take effect." -ForegroundColor Yellow
    Write-Host "`nThen verify with: poetry --version" -ForegroundColor Cyan
}
catch {
    Write-Host "`nError adding to PATH: $_" -ForegroundColor Red
    Write-Host "`nManual steps:" -ForegroundColor Yellow
    Write-Host "1. Open: System Properties > Environment Variables" -ForegroundColor White
    Write-Host "2. Edit 'Path' under User variables" -ForegroundColor White
    Write-Host "3. Add: $PoetryPath" -ForegroundColor White
    exit 1
}
