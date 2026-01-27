<#
.SYNOPSIS
    Gracefully shutdown Neo4j and Omega_KG services for power loss scenarios.

.DESCRIPTION
    This script should be called by UPS software or Windows shutdown scripts
    to ensure Neo4j completes pending transactions and checkpoints before
    system power loss. Can also be used for manual graceful shutdowns.

.PARAMETER TimeoutSeconds
    Maximum time to wait for graceful shutdown before forcing. Default: 120s

.EXAMPLE
    .\graceful-shutdown.ps1
    Standard graceful shutdown with 2 minute timeout

.EXAMPLE
    .\graceful-shutdown.ps1 -TimeoutSeconds 60
    Quick shutdown with 1 minute timeout
#>

param(
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN"  { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

Write-Log "============================================" "INFO"
Write-Log "Neo4j Graceful Shutdown Initiated" "INFO"
Write-Log "============================================" "INFO"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot

try {
    # Check if containers are running
    $neo4jRunning = docker ps --filter "name=apexsigma.neo4j.db" --format "{{.Names}}"

    if (-not $neo4jRunning) {
        Write-Log "Neo4j container not running. Nothing to shutdown." "WARN"
        exit 0
    }

    Write-Log "Found running Neo4j container: $neo4jRunning" "INFO"

    # Step 1: Stop accepting new connections (if capture server is running)
    $captureRunning = Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*capture_server*" }

    if ($captureRunning) {
        Write-Log "Stopping capture server (PID: $($captureRunning.Id))..." "INFO"
        Stop-Process -Id $captureRunning.Id -Force
        Start-Sleep -Seconds 2
    }

    # Step 2: Force Neo4j checkpoint to flush pending transactions
    Write-Log "Forcing Neo4j checkpoint to flush pending transactions..." "INFO"
    docker exec apexsigma.neo4j.db cypher-shell -u $env:NEO4J_USER -p $env:NEO4J_PASSWORD `
        "CALL dbms.checkpoint();" 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Log "Checkpoint completed successfully" "SUCCESS"
    } else {
        Write-Log "Checkpoint command failed, but continuing shutdown..." "WARN"
    }

    Start-Sleep -Seconds 2

    # Step 3: Graceful docker-compose stop with timeout
    Write-Log "Initiating docker-compose stop (timeout: ${TimeoutSeconds}s)..." "INFO"
    $stopJob = Start-Job -ScriptBlock {
        param($root)
        Set-Location $root
        docker-compose stop neo4j-db
    } -ArgumentList $projectRoot

    $completed = Wait-Job $stopJob -Timeout $TimeoutSeconds

    if ($completed) {
        $result = Receive-Job $stopJob
        Remove-Job $stopJob
        Write-Log "Neo4j stopped gracefully" "SUCCESS"
    } else {
        Write-Log "Graceful stop timeout exceeded. Forcing shutdown..." "WARN"
        Stop-Job $stopJob
        Remove-Job $stopJob
        docker stop apexsigma.neo4j.db --time 10
        Write-Log "Neo4j forced to stop" "WARN"
    }

    # Step 4: Verify container is stopped
    $stillRunning = docker ps --filter "name=apexsigma.neo4j.db" --format "{{.Names}}"
    if ($stillRunning) {
        Write-Log "Container still running, forcing kill..." "ERROR"
        docker kill apexsigma.neo4j.db
    }

    Write-Log "============================================" "SUCCESS"
    Write-Log "Graceful Shutdown Complete" "SUCCESS"
    Write-Log "============================================" "SUCCESS"

} catch {
    Write-Log "Error during shutdown: $_" "ERROR"
    exit 1
} finally {
    Pop-Location
}

exit 0
