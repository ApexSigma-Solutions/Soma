# ============================================================
# Omega_KG Virtual Environment Auto-Activation Script (v2 - Relative)
# ============================================================
# Source this from your PowerShell profile.
# v2: Uses relative paths to fix context-bleed.

function Enable-OmegaVenv {
    <#
    .SYNOPSIS
    Enables the virtual environment in the CURRENT directory.
    #>

    # --- FIX: Use relative path from current directory ---
    # $venvPath = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\.venv" # OLD HARDCODED PATH
    $venvPath = Join-Path (Get-Location).Path ".venv" # NEW RELATIVE PATH

    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

    if (Test-Path $activateScript) {
        & $activateScript
        Write-Host "✅ Activated .venv for $(Split-Path (Get-Location).Path -Leaf)" -ForegroundColor Green
        Write-Host "   Python: $(python --version)" -ForegroundColor Gray
        Write-Host "   Poetry: $(poetry --version)" -ForegroundColor Gray
    } else {
        Write-Host "⚠️  Virtual environment not found at: $venvPath" -ForegroundColor Yellow
        Write-Host "   Run: python -m venv .venv" -ForegroundColor Yellow
    }
}

function Disable-OmegaVenv {
    <#
    .SYNOPSIS
    Disables the Omega_KG virtual environment
    #>
    if ($env:VIRTUAL_ENV) {
        deactivate
        Write-Host "✅ Deactivated virtual environment" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  No virtual environment is currently active" -ForegroundColor Yellow
    }
}

# Create convenient aliases
Set-Alias -Name activate-omega -Value Enable-OmegaVenv -Force -Scope Global
Set-Alias -Name deactivate-omega -Value Disable-OmegaVenv -Force -Scope Global

# Add Poetry to PATH if not already present
if ($env:PATH -notmatch "Python\\Scripts") {
    $env:PATH = "$env:APPDATA\Python\Scripts;$env:PATH"
    Write-Host "✨ Added Poetry to PATH" -ForegroundColor Cyan
}

# --- FIX: Auto-activate if a .venv is present, not based on name ---
if (Test-Path (Join-Path (Get-Location).Path ".venv")) {
    Enable-OmegaVenv
}

Write-Host "✨ Omega_KG venv automation ready:" -ForegroundColor Green
Write-Host "   activate-omega   - Activate .venv and Poetry" -ForegroundColor Gray
Write-Host "   deactivate-omega - Deactivate .venv" -ForegroundColor Gray
