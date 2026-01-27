# Omega_KG Environment Sync Script
# Direction: STABLE -> DEV
# Purpose: Align codebase after "Hotfix on Production" architecture shift.

$SourcePath = "D:\projects\Omega_KG_stable"
$DestPath   = "D:\projects\Omega_KG_dev"

Write-Host "🚀 Starting Sync: STABLE -> DEV" -ForegroundColor Cyan
Write-Host "   Source: $SourcePath" -ForegroundColor Gray
Write-Host "   Dest:   $DestPath" -ForegroundColor Gray

# 1. Safety Checks
if (-not (Test-Path $DestPath)) {
    Write-Error "❌ Destination path does not exist!"
    exit 1
}

# 2. Define Critical Directories to Mirror
$DirectoriesToSync = @("omega_kg", "scripts", "alembic", "tests")

foreach ($Dir in $DirectoriesToSync) {
    $Src = Join-Path $SourcePath $Dir
    $Dst = Join-Path $DestPath $Dir

    Write-Host "📂 Syncing directory: $Dir..." -NoNewline

    # Robocopy is faster/safer than Copy-Item for recursion
    # /MIR : Mirror (copy new, delete extra in dest)
    # /XD  : Exclude Directories (__pycache__)
    # /NFL /NDL : No File/Dir Logging (Quiet)
    $null = robocopy $Src $Dst /MIR /XD "__pycache__" ".pytest_cache" /NFL /NDL

    if ($LASTEXITCODE -le 7) {
        Write-Host " [OK]" -ForegroundColor Green
    } else {
        Write-Host " [FAIL]" -ForegroundColor Red
    }
}

# 3. Sync Configuration Files (Dependency Management)
$FilesToSync = @("pyproject.toml", "poetry.lock", "alembic.ini", "README.md")

foreach ($File in $FilesToSync) {
    $SrcFile = Join-Path $SourcePath $File
    $DstFile = Join-Path $DestPath $File

    if (Test-Path $SrcFile) {
        Copy-Item $SrcFile $DstFile -Force
        Write-Host "📄 Copied: $File" -ForegroundColor Green
    }
}

# 4. Critical Warning: .ENV
Write-Host "⚠️  Skipping .env file to preserve environment-specific config." -ForegroundColor Yellow
Write-Host "   Ensure D:\projects\Omega_KG_dev\.env points to 'omega_kg_dev' DB!" -ForegroundColor Yellow

# 5. Update Dependencies in DEV
Write-Host "`n📦 Updating Dev Dependencies (AsyncPG/PGVector)..." -ForegroundColor Cyan
Push-Location $DestPath
try {
    # Force sync ensures dev venv matches the lock file exactly
    poetry install --sync
    Write-Host "✅ Dependencies Updated." -ForegroundColor Green
} catch {
    Write-Error "❌ Failed to update dependencies."
} finally {
    Pop-Location
}

Write-Host "`n✨ Sync Complete. 'Dev' is now architecturally identical to 'Stable'." -ForegroundColor Cyan
