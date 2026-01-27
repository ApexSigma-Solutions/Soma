# scripts/pre-commit-full.ps1
# Run full pre-commit suite including WSL2 infra checks

param(
    [switch]$SkipPython,
    [switch]$InfraOnly
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 Running full pre-commit suite..." -ForegroundColor Cyan

# Step 1: Python checks (Windows)
if (-not $InfraOnly) {
    Write-Host "`n📦 Running Python checks (Windows native)..." -ForegroundColor Yellow
    poetry run pre-commit run --all-files
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Python checks failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Python checks passed" -ForegroundColor Green
}

# Step 2: Infra checks (WSL2)
if (-not $SkipPython) {
    Write-Host "`n🐳 Running infrastructure checks (WSL2)..." -ForegroundColor Yellow

    # Check if WSL2 is available
    $wslCheck = wsl --list --quiet 2>$null
    if (-not $wslCheck) {
        Write-Host "⚠️  WSL2 not available, skipping infra checks" -ForegroundColor Yellow
        Write-Host "   Install with: wsl --install -d Ubuntu-24.04" -ForegroundColor Gray
        exit 0
    }

    # Convert Windows path to WSL path
    $repoPath = (Get-Location).Path -replace '\\', '/' -replace 'C:', '/mnt/c'

    # Run infra checks in WSL2
    wsl bash -c "cd '$repoPath' && pre-commit run --all-files --config .pre-commit-config-infra.yaml"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Infrastructure checks failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Infrastructure checks passed" -ForegroundColor Green
}

Write-Host "`n✨ All checks passed!" -ForegroundColor Green
