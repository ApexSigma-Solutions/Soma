$ProfilePath = $PROFILE
Write-Host "Updating Profile at: $ProfilePath"

if (-not (Test-Path $ProfilePath)) {
    Write-Error "Profile not found at $ProfilePath"
    exit 1
}

$Content = Get-Content $ProfilePath -Raw

# 1. Fix Project Root
# Regex handles both single and double quotes, and potential variations in spacing
$Content = $Content -replace '(?i)\$global:OMEGA_KG_PROJECT_ROOT\s*=\s*(["''])D:\\projects\\Omega_KG_(dev|stable)\1', '$global:OMEGA_KG_PROJECT_ROOT = "d:\projects\OmegaKG"'

# 2. Update Prompt Logic to force [ApexSigma]
# We look for the line calculating $projectName and replace the block
$originalPromptLogic = '(?s)\$projectName\s*=\s*if\s*\(\$global:OMEGA_KG_PROJECT_ROOT\).*?else\s*\{\s*""\s*\}'
$newPromptLogic = '$projectName = if ($global:OMEGA_KG_PROJECT_ROOT) { "[ApexSigma] " } else { "" }'
$Content = $Content -replace $originalPromptLogic, $newPromptLogic

# 3. Update Venv Script Path
# Pattern: Join-Path ... "scripts\omega-venv.ps1"
$Content = $Content -replace [regex]::Escape('"scripts\omega-venv.ps1"'), '"Omega_KG_stable\scripts\maintenance\setup-venv.ps1"'

# 4. Update Pre-flight Check Script Path
# Pattern: Join-Path ... "scripts" ... "Start-OmegaKGDev.ps1"
# We need to handle the nested Join-Path structure or direct strings
# Based on the debug dump: $checkScript = Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"
$Content = $Content -replace [regex]::Escape('Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"'), 'Join-Path $global:OMEGA_KG_PROJECT_ROOT "Omega_KG_stable\scripts\startup") "start-dev.ps1"'

# 5. Fix omega-code function paths to be sure
$Content = $Content -replace [regex]::Escape('"d:\projects\Omega_KG_stable"'), '"d:\projects\OmegaKG"'
$Content = $Content -replace [regex]::Escape('"d:\projects\Omega_KG_dev"'), '"d:\projects\OmegaKG"'


# Backup and Save
$BackupPath = "$ProfilePath.bak_ApexSigma_$(Get-Date -Format 'yyyyMMddHHmmss')"
Copy-Item $ProfilePath $BackupPath
Set-Content -Path $ProfilePath -Value $Content
Write-Host "Profile updated successfully!"
Write-Host "Backup saved to: $BackupPath"
Write-Host "IMPORTANT: Run '. `$PROFILE' to apply changes immediately."
