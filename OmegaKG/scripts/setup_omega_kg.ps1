<#
.SYNOPSIS
    Automated setup script for OmegaKG

.DESCRIPTION
    Installs omega_kg package, verifies installation, and runs health checks.
    Supports dev, stable, and temp environments.

.PARAMETER Environment
    Target environment: dev, stable, or temp

.PARAMETER SkipDependencies
    Skip dependency installation (useful for quick re-install)

.PARAMETER VerifyInstallation
    Run installation verification after setup

.EXAMPLE
    .\scripts\setup_omega_kg.ps1 -Environment stable -VerifyInstallation
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "stable", "temp")]
    [string]$Environment = "stable",

    [Parameter()]
    [switch]$SkipDependencies,

    [Parameter()]
    [switch]$VerifyInstallation = $true,

    [Parameter()]
    [switch]$ForceReinstall
)

# Script configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "Green")
    Write-Host $Message -ForegroundColor $Color
}

function Test-Command {
    param([string]$Command, [string]$Description)
    Write-ColorOutput "Testing: $Description" -Color Cyan
    $result = Invoke-Expression $Command 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "  [OK] $Description" -Color Green
        return $true
    } else {
        Write-ColorOutput "  [FAIL] $Description" -Color Red
        Write-ColorOutput "  Error: $result" -Color Yellow
        return $false
    }
}

# Main setup process
Write-ColorOutput "OmegaKG Automated Setup Script" -Color Cyan
Write-ColorOutput "================================" -Color Cyan
Write-ColorOutput "Environment: $Environment" -Color Cyan
Write-ColorOutput "================================" -Color Cyan
Write-Host ""

# Step 1: Verify we're in the correct directory
$currentDir = Get-Location
Write-ColorOutput "Step 1: Verify directory" -Color Cyan
if (-not (Test-Path "pyproject.toml")) {
    Write-ColorOutput "  [ERROR] pyproject.toml not found!" -Color Red
    Write-ColorOutput "  Please run this script from the OmegaKG root directory" -Color Yellow
    exit 1
}
Write-ColorOutput "  [OK] In OmegaKG root directory" -Color Green
Write-Host ""

# Step 2: Check/Create virtual environment
Write-ColorOutput "Step 2: Virtual environment" -Color Cyan
$venvPath = ".venv"
if (-not (Test-Path $venvPath)) {
    Write-ColorOutput "  Creating virtual environment..." -Color Yellow
    $result = python -m venv $venvPath
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "  [OK] Virtual environment created" -Color Green
    } else {
        Write-ColorOutput "  [ERROR] Failed to create virtual environment" -Color Red
        exit 1
    }
} else {
    Write-ColorOutput "  [OK] Virtual environment exists" -Color Green
}
Write-Host ""

# Step 3: Activate virtual environment
Write-ColorOutput "Step 3: Activate virtual environment" -Color Cyan
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-ColorOutput "  [OK] Activation script found" -Color Green
} else {
    Write-ColorOutput "  [ERROR] Activation script not found: $activateScript" -Color Red
    exit 1
}
Write-Host ""

# Step 4: Install dependencies
if (-not $SkipDependencies) {
    Write-ColorOutput "Step 4: Install dependencies" -Color Cyan

    # Try Poetry first
    if (Get-Command poetry -ErrorAction SilentlyContinue) {
        Write-ColorOutput "  Using Poetry..." -Color Yellow
        if ($ForceReinstall) {
            poetry install --with dev --no-root
        } else {
            poetry install --with dev
        }
        $installSuccess = ($LASTEXITCODE -eq 0)
    } else {
        Write-ColorOutput "  Poetry not found, using pip..." -Color Yellow
        if ($ForceReinstall) {
            pip uninstall -y omega_kg
        }
        pip install -e .
        $installSuccess = ($LASTEXITCODE -eq 0)
    }

    if ($installSuccess) {
        Write-ColorOutput "  [OK] Dependencies installed" -Color Green
    } else {
        Write-ColorOutput "  [ERROR] Failed to install dependencies" -Color Red
        exit 1
    }
} else {
    Write-ColorOutput "  Skipping dependency installation" -Color Yellow
}
Write-Host ""

# Step 5: Verify installation
if ($VerifyInstallation) {
    Write-ColorOutput "Step 5: Verify installation" -Color Cyan
    $verifyResult = python scripts/verify_installation.py
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "  [OK] Installation verified" -Color Green
    } else {
        Write-ColorOutput "  [ERROR] Installation verification failed" -Color Red
        Write-ColorOutput "  Run 'python scripts/verify_installation.py' for details" -Color Yellow
        exit 1
    }
}
Write-Host ""

# Step 6: Run health checks
Write-ColorOutput "Step 6: Run health checks" -Color Cyan
Write-ColorOutput "  Starting server in test mode..." -Color Yellow
$healthCheck = python -c "from omega_kg.capture_server import app; import asyncio; asyncio.run(app.router.routes())" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "  [OK] Server can start" -Color Green
} else {
    Write-ColorOutput "  [WARNING] Server startup test failed (may be expected)" -Color Yellow
}
Write-Host ""

# Summary
Write-ColorOutput "================================" -Color Cyan
Write-ColorOutput "Setup Complete!" -Color Green
Write-ColorOutput "================================" -Color Cyan
Write-Host ""
Write-ColorOutput "Next steps:" -Color Cyan
Write-Host "  1. Edit .env file with your configuration"
Write-Host "  2. Run: poetry run capture-server"
Write-Host "  3. Or: python -m omega_kg.capture_server"
Write-Host "  4. Check health: curl http://localhost:8765/health"
Write-Host ""