# Ollama Heartbeat Monitor
# Phase 5: Continuous Service Monitoring
# Logs status to PostgreSQL datalake for uptime visibility

$ErrorActionPreference = "Stop"

# Configuration
$ollamaUrl = "http://localhost:11434"
$checkIntervalSeconds = 30
$logFile = "ollama_heartbeat.log"
$enablePostgresLogging = $true  # Set to $false to disable PostgreSQL logging

# PostgreSQL connection settings (from Omega_KG environment)
$pgHost = $env:POSTGRES_SERVER
$pgPort = $env:POSTGRES_PORT
$pgUser = $env:POSTGRES_USER
$pgPassword = $env:POSTGRES_PASSWORD
$pgDatabase = $env:POSTGRES_DB

Write-Host "💓 Ollama Heartbeat Monitor" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green
Write-Host "Monitoring Ollama service at: $ollamaUrl" -ForegroundColor Cyan
Write-Host "Check interval: $checkIntervalSeconds seconds" -ForegroundColor Cyan
Write-Host "Log file: $logFile" -ForegroundColor Cyan

# Validate PostgreSQL environment variables if logging is enabled
if ($enablePostgresLogging) {
    $missingVars = @()
    if (-not $pgHost) { $missingVars += 'POSTGRES_SERVER' }
    if (-not $pgPort) { $missingVars += 'POSTGRES_PORT' }
    if (-not $pgUser) { $missingVars += 'POSTGRES_USER' }
    if (-not $pgPassword) { $missingVars += 'POSTGRES_PASSWORD' }
    if (-not $pgDatabase) { $missingVars += 'POSTGRES_DB' }

    if ($missingVars.Count -gt 0) {
        Write-Host "⚠️  Missing environment variables: $($missingVars -join ', ')" -ForegroundColor Yellow
        Write-Host "   PostgreSQL logging will be disabled" -ForegroundColor Yellow
        $enablePostgresLogging = $false
    }
    else {
        Write-Host "PostgreSQL logging: Enabled" -ForegroundColor Cyan
    }
}

# Load Npgsql assembly once at startup
$script:NpgsqlLoaded = $false
if ($enablePostgresLogging) {
    $npgsqlPaths = @(
        "C:\Program Files\PowerShell\Modules\Npgsql\4.1.3.1\lib\netstandard2.0\Npgsql.dll",
        "C:\Program Files\PowerShell\7\Modules\Npgsql\*\lib\netstandard2.0\Npgsql.dll",
        "$env:USERPROFILE\.nuget\packages\npgsql\*\lib\netstandard2.0\Npgsql.dll"
    )

    foreach ($pathPattern in $npgsqlPaths) {
        $foundPath = Get-Item $pathPattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($foundPath) {
            try {
                Add-Type -Path $foundPath.FullName -ErrorAction Stop
                $script:NpgsqlLoaded = $true
                Write-Host "Npgsql loaded from: $($foundPath.FullName)" -ForegroundColor DarkGray
                break
            }
            catch {
                # Already loaded or error, continue
                if ($_.Exception.Message -like "*already exists*") {
                    $script:NpgsqlLoaded = $true
                    break
                }
            }
        }
    }

    if (-not $script:NpgsqlLoaded) {
        Write-Host "⚠️  Npgsql assembly not found. PostgreSQL logging disabled." -ForegroundColor Yellow
        $enablePostgresLogging = $false
    }
}

# Function to log to file
function Write-Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $message"
    Write-Host $logEntry
    Add-Content -Path $logFile -Value $logEntry
}

# Function to test Ollama connectivity
function Test-OllamaConnection {
    try {
        $response = Invoke-RestMethod -Uri "$ollamaUrl/" -Method Get -TimeoutSec 5
        return $true, $response
    }
    catch {
        return $false, $_.Exception.Message
    }
}

# Function to log to PostgreSQL
function Write-ToPostgres {
    param(
        [bool]$isHealthy,
        [string]$statusMessage,
        [datetime]$timestamp,
        [int]$responseTimeMs = 0
    )

    if (-not $enablePostgresLogging -or -not $script:NpgsqlLoaded) {
        return
    }

    $connection = $null
    $command = $null

    try {
        $connectionString = "Server=$pgHost;Port=$pgPort;Database=$pgDatabase;User Id=$pgUser;Password=$pgPassword;"
        $connection = New-Object Npgsql.NpgsqlConnection($connectionString)
        $connection.Open()

        $command = $connection.CreateCommand()
        $command.CommandText = @"
INSERT INTO ollama_heartbeat (
    timestamp,
    is_healthy,
    status_message,
    response_time_ms
) VALUES (
    @timestamp,
    @isHealthy,
    @statusMessage,
    @responseTime
)
"@

        $command.Parameters.Add((New-Object Npgsql.NpgsqlParameter("timestamp", [System.Data.DbType]::DateTime)))
        $command.Parameters["timestamp"].Value = $timestamp

        $command.Parameters.Add((New-Object Npgsql.NpgsqlParameter("isHealthy", [System.Data.DbType]::Boolean)))
        $command.Parameters["isHealthy"].Value = $isHealthy

        $command.Parameters.Add((New-Object Npgsql.NpgsqlParameter("statusMessage", [System.Data.DbType]::String)))
        $command.Parameters["statusMessage"].Value = $statusMessage

        $command.Parameters.Add((New-Object Npgsql.NpgsqlParameter("responseTime", [System.Data.DbType]::Int32)))
        $command.Parameters["responseTime"].Value = $responseTimeMs

        $command.ExecuteNonQuery()
    }
    catch {
        Write-Log "Failed to log to PostgreSQL: $($_.Exception.Message)"
    }
    finally {
        if ($command) { $command.Dispose() }
        if ($connection) {
            if ($connection.State -eq 'Open') { $connection.Close() }
            $connection.Dispose()
        }
    }
}

# Function to create heartbeat table if it doesn't exist
function Create-HeartbeatTable {
    if (-not $enablePostgresLogging -or -not $script:NpgsqlLoaded) {
        return
    }

    $connection = $null
    $command = $null

    try {
        $connectionString = "Server=$pgHost;Port=$pgPort;Database=$pgDatabase;User Id=$pgUser;Password=$pgPassword;"
        $connection = New-Object Npgsql.NpgsqlConnection($connectionString)
        $connection.Open()

        $command = $connection.CreateCommand()
        $command.CommandText = @"
CREATE TABLE IF NOT EXISTS ollama_heartbeat (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    is_healthy BOOLEAN NOT NULL,
    status_message TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ollama_heartbeat_timestamp ON ollama_heartbeat(timestamp);
CREATE INDEX IF NOT EXISTS idx_ollama_heartbeat_healthy ON ollama_heartbeat(is_healthy);
"@

        $command.ExecuteNonQuery()
        Write-Log "Heartbeat table ready"
    }
    catch {
        Write-Log "Failed to create heartbeat table: $($_.Exception.Message)"
    }
    finally {
        if ($command) { $command.Dispose() }
        if ($connection) {
            if ($connection.State -eq 'Open') { $connection.Close() }
            $connection.Dispose()
        }
    }
}

# Initialize
Write-Log "Starting Ollama heartbeat monitor"
Create-HeartbeatTable

$successCount = 0
$failureCount = 0
$lastFailureTime = $null

# Main monitoring loop
try {
    while ($true) {
        $startTime = Get-Date
        $isHealthy, $statusMessage = Test-OllamaConnection
        $endTime = Get-Date
        $responseTime = [math]::Round(($endTime - $startTime).TotalMilliseconds)

        if ($isHealthy) {
            $successCount++
            $failureCount = 0
            $lastFailureTime = $null
            Write-Log "✓ Healthy - $statusMessage (Response: ${responseTime}ms)"
        }
        else {
            $failureCount++
            if ($null -eq $lastFailureTime) {
                $lastFailureTime = Get-Date
            }
            $downtime = [math]::Round((New-TimeSpan -Start $lastFailureTime -End (Get-Date)).TotalSeconds)
            Write-Log "❌ Unhealthy - $statusMessage (Downtime: ${downtime}s, Failures: $failureCount)"
        }

        # Log to PostgreSQL (now includes actual response time)
        Write-ToPostgres -isHealthy $isHealthy -statusMessage $statusMessage -timestamp $startTime -responseTimeMs $responseTime

        # Alert conditions
        if ($failureCount -ge 3) {
            Write-Log "🚨 ALERT: Ollama has been unhealthy for $failureCount consecutive checks!"
            # You could add email/SMS notifications here
        }

        Start-Sleep -Seconds $checkIntervalSeconds
    }
}
catch {
    Write-Log "Monitor stopped with error: $($_.Exception.Message)"
}
finally {
    Write-Log "Ollama heartbeat monitor stopped"
    Write-Log "Summary: $successCount successes, $failureCount failures"
}
