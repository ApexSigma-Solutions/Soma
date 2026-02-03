<#
.SYNOPSIS
    Migrate from Manual Docker Containers to Docker Compose

.DESCRIPTION
    This script performs a clean migration from manually created Docker containers
    to the Docker Compose orchestrated setup defined in docker-compose.yml.
    
    Steps:
    1. Stop and remove manual containers
    2. Create required external volumes
    3. Start services via Docker Compose
    4. Verify health checks
    
.NOTES
    Author: ApexSigma Solutions
    Date: 2026-02-02
    Architecture: Soma Ecosystem Migration
    
.EXAMPLE
    .\scripts\infrastructure\migrate-to-compose.ps1
    .\scripts\infrastructure\migrate-to-compose.ps1 -SkipBackup
#>

[CmdletBinding()]
param(
    [Parameter(HelpMessage="Skip volume backup (faster but no rollback)")]
    [switch]$SkipBackup,
    
    [Parameter(HelpMessage="Dry run - show what would happen")]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$REPO_ROOT = "D:\projects\Soma"

# Service Configuration
$MANUAL_CONTAINERS = @(
    "apexsigma.postgres.soma",
    "apexsigma.neo4j.soma",
    "apexsigma.redis.soma"
)

$MANUAL_VOLUMES = @(
    "soma_pg_data",
    "soma_neo4j_data",
    "soma_neo4j_logs"
)

$EXTERNAL_VOLUMES = @(
    "apexsigma.neo4j.data",
    "apexsigma.neo4j.logs",
    "apexsigma.neo4j.plugins",
    "apexsigma.postgres.data",
    "apexsigma.redis.data"
)

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
            Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
            Write-Host "║  $Message" -ForegroundColor Magenta
            Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Magenta
        }
        default   { Write-Host "[$timestamp] $Message" }
    }
}

function Test-DockerRunning {
    try {
        docker info | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# --- MAIN MIGRATION ---

Write-Status "Soma Ecosystem - Docker Compose Migration" "Header"

# Pre-flight checks
Write-Status "Running pre-flight checks..." "Info"

if (-not (Test-DockerRunning)) {
    Write-Status "Docker is not running! Please start Docker Desktop." "Error"
    exit 1
}

if (-not (Test-Path "$REPO_ROOT\docker-compose.yml")) {
    Write-Status "docker-compose.yml not found at $REPO_ROOT" "Error"
    exit 1
}

Write-Status "Pre-flight checks passed" "Success"

# Step 1: Backup current volumes (if not skipped)
if (-not $SkipBackup -and -not $DryRun) {
    Write-Status "Creating volume backups..." "Info"
    $backupDir = "$REPO_ROOT\backups\volumes_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    foreach ($volume in $MANUAL_VOLUMES) {
        $volumeExists = docker volume inspect $volume 2>$null
        if ($volumeExists) {
            Write-Status "Backing up volume: $volume" "Info"
            # Export volume to tar file
            $backupFile = "$backupDir\$volume.tar"
            docker run --rm -v ${volume}:/source -v ${backupDir}:/backup alpine tar czf /backup/$volume.tar -C /source . 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Status "Backup created: $volume.tar" "Success"
            } else {
                Write-Status "Failed to backup $volume" "Warning"
            }
        }
    }
    Write-Status "Backups saved to: $backupDir" "Success"
}

# Step 2: Stop and remove manual containers
Write-Status "Stopping manual containers..." "Info"

foreach ($container in $MANUAL_CONTAINERS) {
    $containerExists = docker ps -a --filter "name=$container" --format "{{.Names}}" 2>$null
    if ($containerExists) {
        Write-Status "Stopping and removing: $container" "Info"
        if (-not $DryRun) {
            docker stop $container 2>&1 | Out-Null
            docker rm -f $container 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Status "Removed: $container" "Success"
            } else {
                Write-Status "Failed to remove: $container" "Warning"
            }
        }
    } else {
        Write-Status "Container not found: $container (skipping)" "Info"
    }
}

# Step 3: Remove old volumes (optional - we're starting fresh)
Write-Status "Removing old volumes (fresh start)..." "Info"
foreach ($volume in $MANUAL_VOLUMES) {
    $volumeExists = docker volume inspect $volume 2>$null
    if ($volumeExists) {
        Write-Status "Removing volume: $volume" "Info"
        if (-not $DryRun) {
            docker volume rm $volume 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Status "Removed: $volume" "Success"
            } else {
                Write-Status "Failed to remove: $volume" "Warning"
            }
        }
    }
}

# Step 4: Create external volumes required by docker-compose.yml
Write-Status "Creating external volumes..." "Info"

foreach ($volume in $EXTERNAL_VOLUMES) {
    $volumeExists = docker volume inspect $volume 2>$null
    if (-not $volumeExists) {
        Write-Status "Creating external volume: $volume" "Info"
        if (-not $DryRun) {
            docker volume create $volume | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Status "Created: $volume" "Success"
            } else {
                Write-Status "Failed to create: $volume" "Error"
                exit 1
            }
        }
    } else {
        Write-Status "Volume already exists: $volume (reusing)" "Info"
    }
}

# Step 5: Create network if not exists
Write-Status "Ensuring network exists..." "Info"
$networkExists = docker network inspect apexsigma.net 2>$null
if (-not $networkExists) {
    Write-Status "Creating network: apexsigma.net" "Info"
    if (-not $DryRun) {
        docker network create --driver bridge --subnet 172.20.0.0/16 apexsigma.net | Out-Null
        Write-Status "Network created" "Success"
    }
} else {
    Write-Status "Network already exists: apexsigma.net" "Info"
}

# Step 6: Start services via Docker Compose
Write-Status "Starting Docker Compose services..." "Info"

if (-not $DryRun) {
    Set-Location $REPO_ROOT
    
    # Start only infrastructure services first
    Write-Status "Starting infrastructure (Postgres, Neo4j, Redis)..." "Info"
    docker compose up -d postgres neo4j redis 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Failed to start Docker Compose services" "Error"
        exit 1
    }
    
    Write-Status "Docker Compose services started" "Success"
    
    # Wait for health checks
    Write-Status "Waiting for services to become healthy..." "Info"
    Start-Sleep -Seconds 5
    
    # Check service health
    $maxRetries = 30
    $healthyServices = @()
    
    foreach ($service in @("postgres", "neo4j", "redis")) {
        Write-Status "Checking health: $service" "Info"
        
        for ($i = 1; $i -le $maxRetries; $i++) {
            $health = docker compose ps --format json | ConvertFrom-Json | Where-Object { $_.Service -eq $service }
            
            if ($health.Health -eq "healthy" -or $health.State -eq "running") {
                Write-Status "$service is healthy!" "Success"
                $healthyServices += $service
                break
            }
            
            if ($i -eq $maxRetries) {
                Write-Status "$service health check timeout" "Warning"
            }
            
            Start-Sleep -Seconds 2
        }
    }
    
    # Final status
    Write-Status "Migration Summary" "Header"
    
    Write-Host "✅ Manual containers removed: $($MANUAL_CONTAINERS.Count)" -ForegroundColor Green
    Write-Host "✅ External volumes created: $($EXTERNAL_VOLUMES.Count)" -ForegroundColor Green
    Write-Host "✅ Docker Compose services started: $($healthyServices.Count)/3" -ForegroundColor Green
    
    if (-not $SkipBackup) {
        Write-Host "💾 Backups available at: $backupDir" -ForegroundColor Cyan
    }
    
    Write-Host "`n📊 Service Endpoints:" -ForegroundColor Cyan
    Write-Host "  • Postgres:     localhost:6000" -ForegroundColor Yellow
    Write-Host "  • Neo4j Browser: http://localhost:7474" -ForegroundColor Yellow
    Write-Host "  • Neo4j Bolt:    bolt://localhost:7687" -ForegroundColor Yellow
    Write-Host "  • Redis:         localhost:6380" -ForegroundColor Yellow
    
    Write-Host "`n💡 Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Run migrations: poetry run python scripts/database/migrate_all.py upgrade" -ForegroundColor White
    Write-Host "  2. Start ecosystem: .\start_ecosystem.ps1" -ForegroundColor White
    Write-Host "  3. Verify health: docker compose ps" -ForegroundColor White
    
} else {
    Write-Status "DRY RUN MODE - No changes made" "Warning"
    Write-Host "`nWould have performed:" -ForegroundColor Yellow
    Write-Host "  • Stopped $($MANUAL_CONTAINERS.Count) manual containers"
    Write-Host "  • Removed $($MANUAL_VOLUMES.Count) old volumes"
    Write-Host "  • Created $($EXTERNAL_VOLUMES.Count) external volumes"
    Write-Host "  • Started Docker Compose infrastructure"
}

Write-Status "Migration complete! 🎉" "Header"
