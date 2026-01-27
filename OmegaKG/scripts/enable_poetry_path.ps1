# Enable Poetry in System PATH
Write-Host "=== Adding Poetry to System PATH ===" -ForegroundColor Cyan

$poetryPath = "C:\Users\steyn\AppData\Roaming\Python\Python312\Scripts"
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")

# Check if already in PATH
if ($currentPath -split ';' | Where-Object { $_ -eq $poetryPath }) {
    Write-Host "Poetry path already in system PATH!" -ForegroundColor Green
} else {
    # Add to PATH
    $newPath = $currentPath + ";" + $poetryPath
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
    Write-Host "Poetry path added to system PATH!" -ForegroundColor Green
    Write-Host "You may need to restart your terminal/session for changes to take effect." -ForegroundColor Yellow
}

Write-Host "`nVerifying..." -ForegroundColor Cyan
$env:Path = $env:Path + ";$poetryPath"  # Update current session
& where.exe poetry
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Poetry is now accessible!" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Poetry still not found" -ForegroundColor Red
}
