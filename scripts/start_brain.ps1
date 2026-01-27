<#
.SYNOPSIS
    Central Brain Startup Orchestrator for Soma Hybrid Architecture

.DESCRIPTION
    Launches the Soma "Central Brain" system on the Desktop in hybrid mode:
    - State Layer (Docker): Postgres, Neo4j, Redis
    - Logic Layer (Native): InGest (Dagster), OmegaKG (FastAPI), memOS

    This script ensures proper startup sequencing with health checks.

.NOTES
    Author: ApexSigma Solutions
    Date: January 24, 2026
    Architecture: Hybrid Local (Windows Host + Docker State Layer)
#>

[CmdletBinding()]
param(
    [Parameter(HelpMessage="Skip database health checks (faster but risky)")]
    [switch]$SkipHealthCheck,
    
    [Parameter(HelpMessage="Launch only databases (skip application logic)")]
    [switch]$DatabasesOnly,
    
    [Parameter(HelpMessage="Enable verbose logging")]
    [switch]$Verbose
)

# --- CONFIGURATION ---
$ErrorActionPreference = "Stop"
$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$MAX_HEALTH_RETRIES = 30
$HEALTH_CHECK_INTERVAL = 2  # seconds

# Service Ports
$DAGSTER_PORT = 3000
$OMEGAKG_PORT = 8765
$MEMOS_PORT = 8768
$POSTGRES_PORT = 6000
$NEO4J_BOLT_PORT = 7687
$NEO4J_HTTP_PORT = 7474

# --- HELPER FUNCTIONS ---

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Type) {
        "Success" { Write-Host "[$timestamp] ✓ $Message" -ForegroundColor Green }
        "Error"   { Write-Host "[$timestamp] ✗ $Message" -ForegroundColor Red }
        "Warning" { Write-Host "[$timestamp] ⚠ $Message" -ForegroundColor Yellow }
        "Info"    { Write-Host "[$timestamp] ℹ $Message" -ForegroundColor Cyan }
        "Header"  { 
            Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Magenta
            Write-Host "  $Message" -ForegroundColor Magenta
            Write-Host "═══════════════════════════════════════════════════`n" -ForegroundColor Magenta
        }
        default   { Write-Host "[$timestamp] $Message" }
    }
}

function Test-PortListening {
    param([int]$Port, [string]$ServiceName)
    
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Wait-ForService {
    param(
        [int]$Port,
        [string]$ServiceName,
        [int]$MaxRetries = $MAX_HEALTH_RETRIES
    )
    
    Write-Status "Waiting for $ServiceName (port $Port)..." "Info"
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        if (Test-PortListening -Port $Port -ServiceName $ServiceName) {
            Write-Status "$ServiceName is healthy!" "Success"
            return $true
        }
        
        if ($i -eq $MaxRetries) {
            Write-Status "$ServiceName failed to start after $MaxRetries attempts" "Error"
            return $false
        }
        
        Write-Host "  Attempt $i/$MaxRetries..." -NoNewline
        Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL
        Write-Host " ⏳"
    }
}

function Test-PostgresHealth {
    try {
    
        $result = & docker exec apexsigma.postgres.stable pg_isready -U omega_user -d omega_kg_stable 2>&1
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Test-Neo4jHealth {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$NEO4J_HTTP_PORT" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

# --- MAIN ORCHESTRATION ---

Write-Status "Soma Central Brain - Hybrid Startup Orchestrator" "Header"

# Step 1: Navigate to repository root
Write-Status "Setting working directory: $REPO_ROOT" "Info"
Set-Location $REPO_ROOT

# Step 2: Start State Layer (Docker Services)
Write-Status "Starting State Layer (Docker: Postgres, Neo4j, Redis)..." "Info"
try {
    docker-compose up -d postgres neo4j redis
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Failed to start Docker services" "Error"
        exit 1
    }
    Write-Status "Docker services launched" "Success"
}
catch {
    Write-Status "Error starting Docker services: $_" "Error"
    exit 1
}

# Step 3: Health Checks (unless skipped)
if (-not $SkipHealthCheck) {
    Write-Status "Running Health Checks..." "Info"
    
    # Check Postgres
    Write-Status "Checking Postgres..." "Info"
    $postgresHealthy = $false
    for ($i = 1; $i -le $MAX_HEALTH_RETRIES; $i++) {
        if (Test-PostgresHealth) {
            Write-Status "Postgres is healthy!" "Success"
            $postgresHealthy = $true
            break
        }
        Write-Host "  Postgres health check $i/$MAX_HEALTH_RETRIES..." -NoNewline
        Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL
        Write-Host " ⏳"
    }
    
    if (-not $postgresHealthy) {
        Write-Status "Postgres failed health checks" "Error"
        exit 1
    }
    
    # Check Neo4j
    Write-Status "Checking Neo4j..." "Info"
    $neo4jHealthy = $false
    for ($i = 1; $i -le $MAX_HEALTH_RETRIES; $i++) {
        if (Test-Neo4jHealth) {
            Write-Status "Neo4j is healthy!" "Success"
            $neo4jHealthy = $true
            break
        }
        Write-Host "  Neo4j health check $i/$MAX_HEALTH_RETRIES..." -NoNewline
        Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL
        Write-Host " ⏳"
    }
    
    if (-not $neo4jHealthy) {
        Write-Status "Neo4j failed health checks" "Error"
        exit 1
    }
    
    # Check Redis
    if (-not (Wait-ForService -Port 6380 -ServiceName "Redis")) {
        Write-Status "Redis failed to start" "Error"
        exit 1
    }
}

# Exit early if DatabasesOnly flag is set
if ($DatabasesOnly) {
    Write-Status "Database layer started successfully (--DatabasesOnly mode)" "Success"
    Write-Status "Postgres: localhost:$POSTGRES_PORT" "Info"
    Write-Status "Neo4j Browser: http://localhost:$NEO4J_HTTP_PORT" "Info"
    Write-Status "Neo4j Bolt: bolt://localhost:$NEO4J_BOLT_PORT" "Info"
    exit 0
}

# Step 4: Start Logic Layer (Native Applications)
Write-Status "Starting Logic Layer (Native: InGest, OmegaKG)..." "Info"

# Step 4a: Launch InGest (Dagster) in new terminal
Write-Status "Launching InGest (Dagster) on port $DAGSTER_PORT..." "Info"
$ingestPath = Join-Path $REPO_ROOT "InGest"
try {
    $venvPath = Join-Path $ingestPath ".venv"
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$ingestPath'; Write-Host '🧠 InGest (Dagster) Starting...' -ForegroundColor Cyan; Set-Location $ingestPath; & `"$venvPath\Scripts\python.exe` -m dagster dev -h 0.0.0.0 -p $DAGSTER_PORT"
    Write-Status "InGest terminal launched" "Success"
}
catch {
    Write-Status "Failed to launch InGest: $_" "Warning"
}

# Wait a moment before starting next service
Start-Sleep -Seconds 3

# Step 4b: Launch OmegaKG Capture Server (FastAPI) in new terminal
Write-Status "Launching OmegaKG Capture Server on port $OMEGAKG_PORT..." "Info"
$omegakgPath = Join-Path $REPO_ROOT "OmegaKG"
try {
    $venvPath = Join-Path $omegakgPath ".venv"
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$omegakgPath'; Write-Host '🧠 OmegaKG Capture Server Starting...' -ForegroundColor Magenta; Set-Location $omegakgPath; & `"$venvPath\Scripts\python.exe` -m omega_kg.capture_server"
    Write-Status "OmegaKG terminal launched" "Success"
}
catch {
    Write-Status "Failed to launch OmegaKG: $_" "Warning"
}

# Step 5: Summary
Write-Status "Soma Central Brain Startup Complete!" "Header"

Write-Host "`n📊 Service Status:" -ForegroundColor Cyan
Write-Host "  State Layer (Docker):"
Write-Host "    • Postgres:     localhost:$POSTGRES_PORT" -ForegroundColor Green
Write-Host "    • Neo4j Browser: http://localhost:$NEO4J_HTTP_PORT" -ForegroundColor Green
Write-Host "    • Neo4j Bolt:    bolt://localhost:$NEO4J_BOLT_PORT" -ForegroundColor Green
Write-Host "    • Redis:         localhost:6380" -ForegroundColor Green

Write-Host "`n  Logic Layer (Native):"
Write-Host "    • InGest (Dagster):  http://localhost:$DAGSTER_PORT" -ForegroundColor Yellow
Write-Host "    • OmegaKG (Brain):   http://localhost:$OMEGAKG_PORT" -ForegroundColor Yellow
Write-Host "    • memOS:             (Manual start: cd memOS && poetry run python -m memos.server)" -ForegroundColor Gray

Write-Host "`n💡 Tips:" -ForegroundColor Cyan
Write-Host "  • All services bind to 0.0.0.0 for Tailscale access"
Write-Host "  • Use Ctrl+C in each terminal to stop native services"
Write-Host "  • Run 'docker-compose down' to stop state layer"
Write-Host "  • Logs are in separate terminal windows for easy debugging`n"

# Keep this terminal open for user reference
Write-Status "Press any key to close this orchestrator window..." "Info"
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
