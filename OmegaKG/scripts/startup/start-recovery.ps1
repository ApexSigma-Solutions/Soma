<#
.SYNOPSIS
    Start Neo4j with automatic recovery from power failure corruption.

.DESCRIPTION
    Starts Neo4j and attempts automatic recovery if transaction logs are corrupted.
    Validates the database after startup and provides diagnostics.

.EXAMPLE
    .\startup-with-recovery.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN"  { "Yellow" }
        "SUCCESS" { "Green" }
        default { "Cyan" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

Write-Log "============================================" "INFO"
Write-Log "Neo4j Startup with Recovery" "INFO"
Write-Log "============================================" "INFO"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot

try {
    # Load .env
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim() -replace '^"|"$' -replace "^'|'$"
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }

    # Start Neo4j
    Write-Log "Starting Neo4j container..." "INFO"
    docker-compose up -d neo4j-db

    # Wait for startup
    Write-Log "Waiting for Neo4j to start (max 60s)..." "INFO"
    $maxWait = 60
    $waited = 0
    $started = $false

    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 2
        $waited += 2
        
        $logs = docker logs apexsigma.neo4j.db --tail 5 2>&1 | Out-String
        
        if ($logs -match "Started\." -or $logs -match "Remote interface available") {
            $started = $true
            Write-Log "Neo4j started successfully" "SUCCESS"
            break
        }
        
        if ($logs -match "ERROR.*transaction.*log" -or $logs -match "corrupted") {
            Write-Log "Transaction log corruption detected!" "ERROR"
            Write-Log "Attempting automatic recovery..." "WARN"
            
            docker-compose down neo4j-db
            Start-Sleep -Seconds 3
            
            # Restart with recovery enabled (already configured in docker-compose.yml)
            docker-compose up -d neo4j-db
            
            $waited = 0  # Reset wait timer for recovery attempt
            continue
        }
    }

    if (-not $started) {
        Write-Log "Neo4j failed to start within ${maxWait}s" "ERROR"
        Write-Log "Recent logs:" "ERROR"
        docker logs apexsigma.neo4j.db --tail 20
        exit 1
    }

    # Validate connection
    Write-Log "Validating Neo4j connection..." "INFO"
    Start-Sleep -Seconds 5
    
    $testConnection = docker exec apexsigma.neo4j.db cypher-shell -u $env:NEO4J_USER -p $env:NEO4J_PASSWORD `
        "RETURN 'Connection OK' AS status;" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Connection validated successfully" "SUCCESS"
        
        # Get database stats
        $stats = docker exec apexsigma.neo4j.db cypher-shell -u $env:NEO4J_USER -p $env:NEO4J_PASSWORD `
            "MATCH (n) RETURN count(n) AS node_count;" 2>&1 | Select-String -Pattern "\d+"
        
        if ($stats) {
            Write-Log "Database contains nodes: $stats" "INFO"
        }
    } else {
        Write-Log "Connection validation failed" "WARN"
        Write-Log "Output: $testConnection" "WARN"
    }

    Write-Log "============================================" "SUCCESS"
    Write-Log "Startup Complete" "SUCCESS"
    Write-Log "============================================" "SUCCESS"
    Write-Log "Neo4j Browser: http://localhost:7474" "INFO"
    Write-Log "Bolt endpoint: bolt://localhost:7687" "INFO"

} catch {
    Write-Log "Error during startup: $_" "ERROR"
    exit 1
} finally {
    Pop-Location
}

exit 0
