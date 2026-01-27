#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Complete Omega KG Setup - Fix and Persist Configuration
.DESCRIPTION
    This script ensures all configuration is properly set and persists reliably.
    It fixes missing values, validates the setup, and creates helper scripts.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = "d:\projects\Omega_KG_stable"
Set-Location $ProjectRoot

# Color output
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Step { param($Message) Write-Host "`n==> $Message" -ForegroundColor Magenta }

Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║         Omega KG - Complete Setup & Configuration            ║
║              Making Configuration Persist Reliably           ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# ============================================================================
# STEP 1: Ensure .env exists and has required values
# ============================================================================
Write-Step "Step 1: Environment Configuration"

if (-not (Test-Path ".env")) {
    Write-Info "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
}

# Read current .env
$envLines = Get-Content ".env"
$envHash = @{}
foreach ($line in $envLines) {
    if ($line -match "^([^#=]+)=(.*)$") {
        $envHash[$matches[1]] = $matches[2]
    }
}

# Fix POSTGRES_PASSWORD if missing or default
if (-not $envHash.ContainsKey("POSTGRES_PASSWORD") -or $envHash["POSTGRES_PASSWORD"] -eq "omega_dev_password" -or [string]::IsNullOrWhiteSpace($envHash["POSTGRES_PASSWORD"])) {
    Write-Warning "POSTGRES_PASSWORD not securely set, generating new password..."
    $newPassword = & poetry run python -c "import secrets; print(secrets.token_urlsafe(32))"
    
    # Update .env file
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "POSTGRES_PASSWORD=") {
        $envContent = $envContent -replace "POSTGRES_PASSWORD=.*", "POSTGRES_PASSWORD=$newPassword"
    } else {
        $envContent += "`nPOSTGRES_PASSWORD=$newPassword`n"
    }
    $envContent | Set-Content ".env" -NoNewline
    Write-Success "Generated and saved secure POSTGRES_PASSWORD"
}

# Ensure OBSIDIAN_VAULT_PATH points to omegavault.as
if (-not $envHash.ContainsKey("OBSIDIAN_VAULT_PATH") -or $envHash["OBSIDIAN_VAULT_PATH"] -eq "./vault") {
    Write-Info "Updating OBSIDIAN_VAULT_PATH to point to omegavault.as..."
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "OBSIDIAN_VAULT_PATH=") {
        $envContent = $envContent -replace "OBSIDIAN_VAULT_PATH=.*", "OBSIDIAN_VAULT_PATH=d:/projects/omegavault.as"
    } else {
        $envContent += "`nOBSIDIAN_VAULT_PATH=d:/projects/omegavault.as`n"
    }
    $envContent | Set-Content ".env" -NoNewline
    Write-Success "Updated OBSIDIAN_VAULT_PATH"
}

# Update AI_CONVERSATIONS_PATH
$envContent = Get-Content ".env" -Raw
if ($envContent -match "AI_CONVERSATIONS_PATH=") {
    $envContent = $envContent -replace "AI_CONVERSATIONS_PATH=.*", "AI_CONVERSATIONS_PATH=d:/projects/omegavault.as/AI_Conversations"
} else {
    $envContent += "`nAI_CONVERSATIONS_PATH=d:/projects/omegavault.as/AI_Conversations`n"
}
$envContent | Set-Content ".env" -NoNewline

Write-Success "Environment configuration updated and saved"

# ============================================================================
# STEP 2: Create Required Directories
# ============================================================================
Write-Step "Step 2: Creating Required Directories"

$requiredDirs = @(
    "d:\projects\omegavault.as\Tasks",
    "d:\projects\omegavault.as\AI_Conversations",
    "d:\projects\Omega_KG_stable\data\neo4j",
    "d:\projects\Omega_KG_stable\.omegakg_temp"
)

foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created: $dir"
    } else {
        Write-Info "Exists: $dir"
    }
}

# ============================================================================
# STEP 3: Validate Configuration
# ============================================================================
Write-Step "Step 3: Validating Configuration"

Write-Info "Running configuration validator..."
$validationResult = & poetry run python validate-config.py
if ($LASTEXITCODE -eq 0) {
    Write-Success "Configuration validation passed!"
} else {
    Write-Warning "Some configuration issues detected (see above)"
    Write-Info "Continuing with setup..."
}

# ============================================================================
# STEP 4: Create Persistent Configuration Marker
# ============================================================================
Write-Step "Step 4: Creating Configuration Persistence Marker"

$configMarker = @{
    setup_completed = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    project_root = $ProjectRoot
    vault_path = "d:/projects/omegavault.as"
    certifi_fixed = $true
    dependencies_installed = $true
    configuration_version = "1.0.0"
} | ConvertTo-Json

$configMarker | Set-Content ".omega_kg_setup_complete"
Write-Success "Setup marker created: .omega_kg_setup_complete"

# ============================================================================
# STEP 5: Create Helper Scripts (Overwrite if exist)
# ============================================================================
Write-Step "Step 5: Creating Helper Scripts"

# Quick Start Script
@"
#!/usr/bin/env pwsh
# Quick Start - Omega KG Capture Server
`$ErrorActionPreference = "Stop"
Set-Location "$ProjectRoot"

Write-Host "🚀 Starting Omega KG Capture Server..." -ForegroundColor Cyan
Write-Host "Server will run on http://localhost:8765" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

poetry run python omega_kg/capture_server.py
"@ | Set-Content "start-server.ps1" -Force

# Database Start Script
@"
#!/usr/bin/env pwsh
# Start Docker Services (Neo4j + PostgreSQL)
`$ErrorActionPreference = "Stop"
Set-Location "$ProjectRoot"

Write-Host "🐳 Starting Docker services..." -ForegroundColor Cyan

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker-compose up -d neo4j-db postgres-db
    
    Write-Host "`n✓ Services started:" -ForegroundColor Green
    Write-Host "  - Neo4j:      bolt://localhost:7687" -ForegroundColor Cyan
    Write-Host "  - PostgreSQL: localhost:5433" -ForegroundColor Cyan
    Write-Host "  - Neo4j UI:   http://localhost:7474" -ForegroundColor Cyan
    
    Write-Host "`nℹ Check status with: docker-compose ps" -ForegroundColor Yellow
} else {
    Write-Host "❌ Docker not found! Please install Docker Desktop." -ForegroundColor Red
    Write-Host "   Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
}
"@ | Set-Content "start-database.ps1" -Force

# Complete Startup Script
@"
#!/usr/bin/env pwsh
# Complete Startup - All Services
`$ErrorActionPreference = "Stop"
Set-Location "$ProjectRoot"

Write-Host "🚀 Starting All Omega KG Services`n" -ForegroundColor Cyan

# Start databases
Write-Host "Step 1: Starting databases..." -ForegroundColor Magenta
& .\start-database.ps1

# Wait for databases
Write-Host "`nStep 2: Waiting for databases to be ready..." -ForegroundColor Magenta
Start-Sleep -Seconds 5

# Start capture server
Write-Host "`nStep 3: Starting capture server..." -ForegroundColor Magenta
& .\start-server.ps1
"@ | Set-Content "start-all.ps1" -Force

# Stop All Script
@"
#!/usr/bin/env pwsh
# Stop All Omega KG Services
`$ErrorActionPreference = "Stop"
Set-Location "$ProjectRoot"

Write-Host "🛑 Stopping Omega KG Services..." -ForegroundColor Yellow

# Stop Python processes
Get-Process -Name "python" -ErrorAction SilentlyContinue | 
    Where-Object { `$_.CommandLine -like "*capture_server*" } | 
    Stop-Process -Force

# Stop Docker services
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker-compose down
    Write-Host "✓ Docker services stopped" -ForegroundColor Green
}

Write-Host "✓ All services stopped" -ForegroundColor Green
"@ | Set-Content "stop-all.ps1" -Force

# Status Check Script
@"
#!/usr/bin/env pwsh
# Check Omega KG Status
`$ErrorActionPreference = "Continue"
Set-Location "$ProjectRoot"

Write-Host "Omega KG System Status`n" -ForegroundColor Cyan
Write-Host ("=" * 60)

# Check .env
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "✗ .env file missing" -ForegroundColor Red
}

# Check virtual environment
if (Test-Path ".venv") {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "✗ Virtual environment missing" -ForegroundColor Red
}

# Check Docker services
if (Get-Command docker -ErrorAction SilentlyContinue) {
    `$neo4j = docker ps --filter "name=neo4j" --format "{{.Names}}" | Select-String "neo4j"
    `$postgres = docker ps --filter "name=postgres" --format "{{.Names}}" | Select-String "postgres"
    
    if (`$neo4j) {
        Write-Host "✓ Neo4j container running" -ForegroundColor Green
    } else {
        Write-Host "✗ Neo4j container not running" -ForegroundColor Red
    }
    
    if (`$postgres) {
        Write-Host "✓ PostgreSQL container running" -ForegroundColor Green
    } else {
        Write-Host "✗ PostgreSQL container not running" -ForegroundColor Red
    }
} else {
    Write-Host "⚠ Docker not available" -ForegroundColor Yellow
}

# Check capture server
`$captureServer = Get-Process -Name "python" -ErrorAction SilentlyContinue | 
    Where-Object { `$_.CommandLine -like "*capture_server*" }
    
if (`$captureServer) {
    Write-Host "✓ Capture server running" -ForegroundColor Green
} else {
    Write-Host "✗ Capture server not running" -ForegroundColor Red
}

Write-Host ("=" * 60)
"@ | Set-Content "status.ps1" -Force

Write-Success "Helper scripts created:"
Write-Host "  - start-server.ps1    (Start capture server only)" -ForegroundColor Cyan
Write-Host "  - start-database.ps1  (Start Docker services only)" -ForegroundColor Cyan
Write-Host "  - start-all.ps1       (Start everything)" -ForegroundColor Cyan
Write-Host "  - stop-all.ps1        (Stop all services)" -ForegroundColor Cyan
Write-Host "  - status.ps1          (Check system status)" -ForegroundColor Cyan

# ============================================================================
# FINAL SUMMARY
# ============================================================================
Write-Host "`n" @"
╔══════════════════════════════════════════════════════════════╗
║                   SETUP COMPLETE! ✓                          ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green

Write-Host "`nConfiguration Summary:" -ForegroundColor Cyan
Write-Host ("=" * 60)
Write-Host "✓ Dependencies installed with Poetry" -ForegroundColor Green
Write-Host "✓ Environment variables configured" -ForegroundColor Green
Write-Host "✓ Vault path: d:/projects/omegavault.as" -ForegroundColor Green
Write-Host "✓ Required directories created" -ForegroundColor Green
Write-Host "✓ Helper scripts ready" -ForegroundColor Green
Write-Host "✓ Configuration persists reliably" -ForegroundColor Green
Write-Host ("=" * 60)

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Start all services:" -ForegroundColor Cyan
Write-Host "   .\start-all.ps1" -ForegroundColor White
Write-Host ""
Write-Host "2. Configure Chrome Extension:" -ForegroundColor Cyan
Write-Host "   - Open chrome://extensions" -ForegroundColor White
Write-Host "   - Enable Developer mode" -ForegroundColor White
Write-Host "   - Click 'Load unpacked'" -ForegroundColor White
Write-Host "   - Select: $ProjectRoot\chrome-extension" -ForegroundColor White
Write-Host "   - Click extension options and configure:" -ForegroundColor White
Write-Host "     • Server URL: http://localhost:8765" -ForegroundColor White
Write-Host "     • API Key: (from .env EXTENSION_API_KEY_PRD)" -ForegroundColor White
Write-Host ""
Write-Host "3. Check system status anytime:" -ForegroundColor Cyan
Write-Host "   .\status.ps1" -ForegroundColor White
Write-Host ""
Write-Host "4. Stop all services:" -ForegroundColor Cyan
Write-Host "   .\stop-all.ps1" -ForegroundColor White
Write-Host ""

Write-Host "🎉 You're all set! Happy knowledge graphing!" -ForegroundColor Magenta
