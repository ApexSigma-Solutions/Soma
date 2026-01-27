$ProfilePath = $PROFILE
Write-Host "Forcing Update on Profile at: $ProfilePath"

if (-not (Test-Path $ProfilePath)) {
    Write-Error "Profile not found at $ProfilePath"
    exit 1
}

$Content = Get-Content $ProfilePath -Raw

# Helper to debug replacements
function Replace-Text {
    param($InputString, $Old, $New)
    if ($InputString.Contains($Old)) {
        Write-Host "  [+] Replacing: '$Old'" -ForegroundColor Green
        return $InputString.Replace($Old, $New)
    } else {
        Write-Host "  [-] Not Found: '$Old'" -ForegroundColor Yellow
        return $InputString
    }
}

# 1. Fix Project Root Variable
$Content = Replace-Text -InputString $Content -Old '$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\Omega_KG_dev"' -New '$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\OmegaKG"'

# 2. Fix Prompt
$OldPrompt = '$projectName = if ($global:OMEGA_KG_PROJECT_ROOT) { "[$([System.IO.Path]::GetFileName($global:OMEGA_KG_PROJECT_ROOT))] " } else { "" }'
$NewPrompt = '$projectName = if ($global:OMEGA_KG_PROJECT_ROOT) { "[ApexSigma] " } else { "" }'
$Content = Replace-Text -InputString $Content -Old $OldPrompt -New $NewPrompt

# 3. Fix venv script path
$Content = Replace-Text -InputString $Content -Old '"scripts\omega-venv.ps1"' -New '"Omega_KG_stable\scripts\maintenance\setup-venv.ps1"'

# 4. Fix Check Script logic (The tricky Join-Path one)
# Line 274: $checkScript = Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"
$OldCheck = 'Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"'
$NewCheck = 'Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "Omega_KG_stable\scripts\startup") "start-dev.ps1"'
$Content = Replace-Text -InputString $Content -Old $OldCheck -New $NewCheck

# 5. Fix omega-code (just in case)
$Content = Replace-Text -InputString $Content -Old '"d:\projects\Omega_KG_stable"' -New '"d:\projects\OmegaKG"'
$Content = Replace-Text -InputString $Content -Old '"d:\projects\Omega_KG_dev"' -New '"d:\projects\OmegaKG"'

# 6. Disable the Environment Switcher dynamic path
$Content = Replace-Text -InputString $Content -Old '$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\Omega_KG_$Environment"' -New '$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\OmegaKG"'

# Save
Set-Content -Path $ProfilePath -Value $Content
Write-Host "Force update complete."
