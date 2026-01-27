$ProfilePath = $PROFILE
Write-Host "Forcing V2 Update on Profile at: $ProfilePath"

if (-not (Test-Path $ProfilePath)) {
    Write-Error "Profile not found at $ProfilePath"
    exit 1
}

$Lines = Get-Content $ProfilePath
$NewLines = @()
$Changes = 0

foreach ($Line in $Lines) {
    $Trimmed = $Line.Trim()
    
    # 1. Fix Project Root Calculation
    if ($Trimmed -like '*$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\Omega_KG_dev"*') {
        Write-Host "  [+] Fixing Root Path (Dev)" -ForegroundColor Green
        $NewLines += '$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\OmegaKG"'
        $Changes++
    }
    elseif ($Trimmed -like '*$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\Omega_KG_$Environment"*') {
         Write-Host "  [+] Fixing Root Path (Dynamic)" -ForegroundColor Green
         $NewLines += '    $global:OMEGA_KG_PROJECT_ROOT = "D:\projects\OmegaKG"'
         $Changes++
    }
    # 2. Fix Prompt Display
    elseif ($Trimmed -like '*$projectName = if ($global:OMEGA_KG_PROJECT_ROOT)*') {
        Write-Host "  [+] Fixing Prompt Name" -ForegroundColor Green
        $NewLines += '    $projectName = if ($global:OMEGA_KG_PROJECT_ROOT) { "[ApexSigma] " } else { "" }'
        $Changes++
    }
    # 3. Fix Venv Script Path
    elseif ($Trimmed -like '*scripts\omega-venv.ps1*') {
        Write-Host "  [+] Fixing Venv Script Path" -ForegroundColor Green
        $NewLines += '$venvScriptPath = Join-Path $global:OMEGA_KG_PROJECT_ROOT "Omega_KG_stable\scripts\maintenance\setup-venv.ps1"'
        $Changes++
    }
    # 4. Fix Pre-flight Check Script
    elseif ($Trimmed -like '*Start-OmegaKGDev.ps1*') {
         Write-Host "  [+] Fixing Pre-flight Script Path" -ForegroundColor Green
         $NewLines += '    $checkScript = Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "Omega_KG_stable\scripts\startup") "start-dev.ps1"'
         $Changes++
    }
    # 5. Fix omega-code paths
    elseif ($Trimmed -like '*"d:\projects\Omega_KG_stable"*') {
        Write-Host "  [+] Fixing omega-code path (stable)" -ForegroundColor Green
        $NewLines += '        "d:\projects\OmegaKG"'
        $Changes++
    }
    elseif ($Trimmed -like '*"d:\projects\Omega_KG_dev"*') {
        Write-Host "  [+] Fixing omega-code path (dev)" -ForegroundColor Green
        $NewLines += '        "d:\projects\OmegaKG"'
        $Changes++
    }
    else {
        $NewLines += $Line
    }
}

if ($Changes -gt 0) {
    Set-Content -Path $ProfilePath -Value $NewLines
    Write-Host "Success! Made $Changes replacements."
} else {
    Write-Warning "No lines matched the patterns. Profile might already be updated or patterns are wrong."
}
