#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Omega KG Project Setup Script
.DESCRIPTION
    Automated setup and configuration validation for Omega KG project.
    Ensures all dependencies, configuration, and services are properly configured and persist reliably.
#>

param(
    [switch]$SkipDocker,
    [switch]$SkipPoetry,
    [switch]$Verify
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# Color output helpers
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Step { param($Message) Write-Host "`n==> $Message" -ForegroundColor Magenta }

# ============================================================================
# STEP 1: Environment File Configuration
# ============================================================================
Write-Step "Checking Environment Configuration"

if (-not (Test-Path ".env")) {
    Write-Info "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Warning ".env created! You MUST configure the following:"
    Write-Host "  1. NEO4J_PASSWORD - Set a secure password"
    Write-Host "  2. POSTGRES_PASSWORD - Set a secure password"
    Write-Host "  3. EXTENSION_API_KEY_PRD - Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    Write-Host "  4. JWT_SECRET_KEY - Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    Write-Host "  5. CHROME_EXTENSION_ID - Get from chrome://extensions"
    Write-Host "`nRun this script again after configuring .env"
    exit 1
} else {
    Write-Success ".env file exists"
}

# Validate critical environment variables
$envContent = Get-Content ".env" -Raw
$criticalVars = @{
    "NEO4J_PASSWORD" = "change_me_secure_password"
    "POSTGRES_PASSWORD" = "omega_dev_password"
    "EXTENSION_API_KEY_PRD" = "change_me_secure_api_key"
    "JWT_SECRET_KEY" = "change_me_to_secure_random_string"
}

$needsConfig = $false
foreach ($var in $criticalVars.Keys) {
    $defaultValue = $criticalVars[$var]
    if ($envContent -match "$var=$defaultValue") {
        Write-Warning "$var is still using the default value - SECURITY RISK!"
        $needsConfig = $true
    }
}

if ($needsConfig -and -not $Verify) {
    Write-Error "Critical security configuration needed! Update .env with secure values."
    Write-Info "Generate secure values with:"
    Write-Host "  python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    exit 1
}

# ============================================================================
# STEP 2: Poetry Installation Check
# ============================================================================
Write-Step "Checking Poetry Installation"

try {
    $poetryVersion = poetry --version
    Write-Success "Poetry installed: $poetryVersion"
} catch {
    Write-Error "Poetry not found! Install from: https://python-poetry.org/docs/#installation"
    exit 1
}

# ============================================================================
# STEP 3: Python Dependencies
# ============================================================================
if (-not $SkipPoetry) {
    Write-Step "Installing Python Dependencies"
    
    Write-Info "Installing dependencies with Poetry..."
    poetry install --with dev
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python dependencies installed"
    } else {
        Write-Error "Poetry install failed"
        exit 1
    }
} else {
    Write-Info "Skipping Poetry install (--SkipPoetry flag set)"
}

# ============================================================================
# STEP 4: Docker Services Check
# ============================================================================
if (-not $SkipDocker) {
    Write-Step "Checking Docker Services"
    
    try {
        docker --version | Out-Null
        Write-Success "Docker is available"
        
        # Check if services are running
        $neo4jRunning = docker ps --filter "name=neo4j" --format "{{.Names}}" | Select-String "neo4j"
        $postgresRunning = docker ps --filter "name=postgres" --format "{{.Names}}" | Select-String "postgres"
        
        if (-not $neo4jRunning) {
            Write-Warning "Neo4j container not running"
            Write-Info "Start with: docker-compose up -d neo4j-db"
        } else {
            Write-Success "Neo4j container is running"
        }
        
        if (-not $postgresRunning) {
            Write-Warning "PostgreSQL container not running"
            Write-Info "Start with: docker-compose up -d postgres-db"
        } else {
            Write-Success "PostgreSQL container is running"
        }
        
    } catch {
        Write-Warning "Docker not available - you'll need to run Neo4j and PostgreSQL manually"
    }
} else {
    Write-Info "Skipping Docker checks (--SkipDocker flag set)"
}

# ============================================================================
# STEP 5: Database Migration
# ============================================================================
Write-Step "Checking Database Migrations"

if (Test-Path ".venv/Scripts/alembic.exe") {
    Write-Info "Running Alembic migrations..."
    poetry run alembic upgrade head
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Database migrations applied"
    } else {
        Write-Warning "Migration may have failed - check if PostgreSQL is running"
    }
} else {
    Write-Warning "Alembic not found - run 'poetry install' first"
}

# ============================================================================
# STEP 6: Configuration Persistence Verification
# ============================================================================
Write-Step "Verifying Configuration Persistence"

# Create .omega_kg_config file to track setup state
$configFile = ".omega_kg_config"
$configData = @{
    last_setup = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    project_root = $ProjectRoot
    python_version = (poetry run python --version)
    poetry_version = (poetry --version)
    vault_path = (Get-Content ".env" | Select-String "^VAULT_PATH=" | ForEach-Object { $_ -replace "VAULT_PATH=", "" })
}

$configData | ConvertTo-Json | Set-Content $configFile
Write-Success "Configuration state saved to $configFile"

# ============================================================================
# STEP 7: Create Helper Scripts
# ============================================================================
Write-Step "Creating Helper Scripts"

# Start script
@"
#!/usr/bin/env pwsh
# Quick start script for Omega KG
Set-Location "$ProjectRoot"
Write-Host "Starting Omega KG Capture Server..." -ForegroundColor Cyan
poetry run python omega_kg/capture_server.py
"@ | Set-Content "start.ps1"

# Stop script
@"
#!/usr/bin/env pwsh
# Stop all Omega KG services
Write-Host "Stopping Omega KG services..." -ForegroundColor Cyan
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { `$_.CommandLine -like "*capture_server*" } | Stop-Process -Force
Write-Host "Services stopped" -ForegroundColor Green
"@ | Set-Content "stop.ps1"

Write-Success "Helper scripts created: start.ps1, stop.ps1"

# ============================================================================
# STEP 8: Final Verification
# ============================================================================
Write-Step "Final Verification"

$checks = @()

# Check .env exists
$checks += [PSCustomObject]@{
    Check = "Environment File"
    Status = (Test-Path ".env")
    Message = ".env configuration file"
}

# Check vault path
$vaultPath = Get-Content ".env" | Select-String "^VAULT_PATH=" | ForEach-Object { $_ -replace "VAULT_PATH=", "" }
if ($vaultPath) {
    $vaultPath = $vaultPath.Trim('"')
    $checks += [PSCustomObject]@{
        Check = "Obsidian Vault"
        Status = (Test-Path $vaultPath)
        Message = "Vault at $vaultPath"
    }
}

# Check poetry.lock
$checks += [PSCustomObject]@{
    Check = "Dependencies Lock"
    Status = (Test-Path "poetry.lock")
    Message = "poetry.lock file exists"
}

# Check virtual environment
$checks += [PSCustomObject]@{
    Check = "Virtual Environment"
    Status = (Test-Path ".venv")
    Message = "Poetry virtual environment"
}

# Display results
Write-Host "`nSetup Verification Results:" -ForegroundColor Cyan
Write-Host ("=" * 60)
foreach ($check in $checks) {
    if ($check.Status) {
        Write-Host "✓" -ForegroundColor Green -NoNewline
    } else {
        Write-Host "✗" -ForegroundColor Red -NoNewline
    }
    Write-Host " $($check.Check): $($check.Message)"
}
Write-Host ("=" * 60)

# ============================================================================
# STEP 9: Next Steps
# ============================================================================
Write-Step "Setup Complete!"

Write-Host "`nNext Steps:"
Write-Host "1. Start Docker services:" -ForegroundColor Cyan
Write-Host "   docker-compose up -d"
Write-Host ""
Write-Host "2. Start the capture server:" -ForegroundColor Cyan
Write-Host "   .\start.ps1"
Write-Host "   # OR"
Write-Host "   poetry run python omega_kg/capture_server.py"
Write-Host ""
Write-Host "3. Configure Chrome Extension:" -ForegroundColor Cyan
Write-Host "   - Open chrome://extensions"
Write-Host "   - Load unpacked from ./chrome-extension"
Write-Host "   - Click extension options"
Write-Host "   - Set Server URL: http://localhost:8765"
Write-Host "   - Set API Key from .env (EXTENSION_API_KEY_PRD)"
Write-Host ""
Write-Host "4. Test the connection:" -ForegroundColor Cyan
Write-Host "   poetry run python -c 'from omega_kg.settings import Settings; s = Settings(); print(f\"Server: {s.app_host}:{s.app_port}\")'"
Write-Host ""

if ($Verify) {
    Write-Host "`nConfiguration is persisted and ready!" -ForegroundColor Green
}
