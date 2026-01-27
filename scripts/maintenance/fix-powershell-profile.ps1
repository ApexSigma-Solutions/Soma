$ProfilePath = $PROFILE
Write-Host "Checking Profile at: $ProfilePath"

if (-not (Test-Path $ProfilePath)) {
    Write-Error "Profile not found at $ProfilePath"
    exit 1
}

$Content = Get-Content $ProfilePath -Raw

# 1. Update Project Root
$Content = $Content -replace [regex]::Escape('D:\projects\Omega_KG_dev'), 'd:\projects\OmegaKG'
$Content = $Content -replace [regex]::Escape('D:\projects\Omega_KG_stable'), 'd:\projects\OmegaKG'

# 2. Update venv script path
# Line 208: Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts\omega-venv.ps1"
# We replace explicitly the string "scripts\omega-venv.ps1" with "Omega_KG_stable\scripts\maintenance\setup-venv.ps1"
$Content = $Content -replace [regex]::Escape('scripts\omega-venv.ps1'), 'Omega_KG_stable\scripts\maintenance\setup-venv.ps1'

# 3. Update Pre-flight check script path
# Profile uses: Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"
# or just "scripts" folder reference.
# We change "scripts" to "Omega_KG_stable\scripts\startup"
# BUT "scripts" is a common word. We need context.
$Content = $Content -replace [regex]::Escape('Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts"'), 'Join-Path $global:OMEGA_KG_PROJECT_ROOT "Omega_KG_stable\scripts\startup"'

# And the file name "Start-OmegaKGDev.ps1" -> "start-dev.ps1"
$Content = $Content -replace [regex]::Escape('Start-OmegaKGDev.ps1'), 'start-dev.ps1'

# Also handle the nested Join-Path case from the dump:
# Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"
# The previous replacement 'Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts"' might not match due to the parenthesis structure if it was `(Join-Path ...)`
# Let's replace just the string literal "scripts" inside that specific context if possible, or simpler:
$Content = $Content -replace [regex]::Escape('"scripts" "Start-OmegaKGDev.ps1"'), '"Omega_KG_stable\scripts\startup" "start-dev.ps1"'

# And catch the case where they are separate args to Join-Path
$Content = $Content -replace [regex]::Escape('"scripts") "Start-OmegaKGDev.ps1"'), '"Omega_KG_stable\scripts\startup") "start-dev.ps1"'


# Backup and Save
$BackupPath = "$ProfilePath.bak_$(Get-Date -Format 'yyyyMMddHHmmss')"
Copy-Item $ProfilePath $BackupPath
Set-Content -Path $ProfilePath -Value $Content
Write-Host "Profile updated successfully!"
Write-Host "Backup saved to: $BackupPath"
Write-Host "Please restart your terminal or run '. `$PROFILE' to apply changes."
