# Omega Ecosystem - Structural Realignment Script
# Objective: Rename legacy folder names to canonical 'Organism' identities.
# Context: Pre-Dagster Refactor

$root = "d:\projects\OmegaKG"
$changes = @{
    "Omega_KG_stable" = "OmegaKG"
    "InGest-LLM.as"   = "InGest"
    "memos.MCP"       = "memOS"
}

Write-Host "Starting Structural Realignment..." -ForegroundColor Cyan

foreach ($old in $changes.Keys) {
    $new = $changes[$old]
    $oldPath = Join-Path $root $old
    $newPath = Join-Path $root $new

    if (Test-Path $oldPath) {
        if (-not (Test-Path $newPath)) {
            Write-Host "Renaming '$old' -> '$new'..." -NoNewline
            try {
                Rename-Item -Path $oldPath -NewName $new -ErrorAction Stop
                Write-Host " [OK]" -ForegroundColor Green
            }
            catch {
                Write-Host " [FAILED]" -ForegroundColor Red
                Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "Skipping '$old': Target '$new' already exists." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Skipping '$old': Source folder not found." -ForegroundColor DarkGray
    }
}

Write-Host "`nUpdate Required:" -ForegroundColor Magenta
Write-Host "1. Update your VS Code Workspace file (Omega_KG.code-workspace)."
Write-Host "2. Update any .env files referencing absolute paths."
Write-Host "3. Re-run 'poetry install' in each new directory."