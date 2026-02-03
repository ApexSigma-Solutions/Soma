#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Soma Ecosystem Startup Script with Pre-flight Checks and Health Monitoring
.DESCRIPTION
    Comprehensive startup orchestrator for the Soma biomorphic ecosystem.
    Features:
    - Pre-flight dependency validation
    - Exponential backoff retry mechanism
    - Fail-fast and fail-loud error handling
    - Verbose structured logging
    - Service health check orchestration
    - Auto-launch to Cortex Dashboard
.NOTES
    Version: 2.0.0
    Author: Soma Ecosystem
    Compliance: ApexSigma Naming, MAR Protocol v2.0, Mirmir Constraints
#>

[CmdletBinding()]
param(
    [switch]$SkipPreflight,
    [switch]$SkipDocker,
    [switch]$VerboseLogging,
    [int]$MaxRetries = 5,
    [int]$InitialBackoffSeconds = 2,
    [string]$LogPath = "$env:USERPROFILE\.soma\logs",
    [switch]$NoBrowser,
    [switch]$DebugMode
)

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

$script:Version = "2.0.0"
$script:StartTime = Get-Date
$script:LogFile = Join-Path $LogPath "soma-startup-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Load environment variables from .env file
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present
            $value = $value -replace '^["'']|["'']$', ''
            # Set in current PowerShell session env (inherited by child processes)
            Set-Item -Path "env:$name" -Value $value -Force
        }
    }
}

# Service Definitions - ApexSigma Biological Terminology
$script:Services = @(
    @{
        Name = "Senses"
        Code = "ING"
        ProcessName = "soma-ingress"
        Port = 8000
        HealthEndpoint = "/health"
        StartupDelay = 2
        Required = $true
        Description = "Sensory input layer - InGress API"
    },
    @{
        Name = "Stomach"
        Code = "DIG"
        ProcessName = "ingest-llm"
        Port = 8766
        HealthEndpoint = "/health"
        StartupDelay = 3
        Required = $true
        Description = "Digestive processing layer - InGest"
    },
    @{
        Name = "Brain"
        Code = "OMG"
        ProcessName = "omega-kg"
        Port = 8765
        HealthEndpoint = "/health"
        StartupDelay = 5
        Required = $true
        Description = "Knowledge graph - OmegaKG"
    },
    @{
        Name = "Bridge"
        Code = "MEM"
        ProcessName = "memos"
        Port = 8768
        HealthEndpoint = "/health"
        StartupDelay = 2
        Required = $true
        Description = "Working memory bridge - memOS"
    },
    @{
        Name = "Cortex"
        Code = "CTX"
        ProcessName = "node"
        Port = 6001
        HealthEndpoint = "/"
        StartupDelay = 3
        Required = $true
        Description = "Dashboard/Observer - Cortex UI"
    }
)

# Infrastructure Dependencies
$script:Infrastructure = @(
    @{
        Name = "PostgreSQL"
        Type = "Database"
        Port = 6000
        Required = $true
        Description = "Raw lake storage"
    },
    @{
        Name = "Neo4j"
        Type = "GraphDatabase"
        Port = 7687
        Required = $true
        Description = "Knowledge graph persistence"
    },
    @{
        Name = "Redis"
        Type = "Cache"
        Port = 6380
        Required = $true
        Description = "Working memory / Nervous system"
    }
)

# Color Codes for Terminal Output
$script:Colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Debug = "Gray"
    Accent = "Magenta"
}

# =============================================================================
# LOGGING SYSTEM
# =============================================================================

function Initialize-Logging {
    param([string]$LogDirectory)
    
    if (-not (Test-Path $LogDirectory)) {
        New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    }
    
    # Create log file with headers
    $headers = @"
================================================================================
SOMA ECOSYSTEM STARTUP LOG
Version: $script:Version
Started: $script:StartTime
Log File: $script:LogFile
================================================================================

"@
    $headers | Out-File -FilePath $script:LogFile -Encoding UTF8
    
    Write-Log "Logging initialized" -Level "INFO"
    Write-Log "Log file: $script:LogFile" -Level "DEBUG"
}

function Write-Log {
    param(
        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string]$Message = "",
        
        [ValidateSet("INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG", "CRITICAL")]
        [string]$Level = "INFO",
        
        [string]$Service = "SYSTEM",
        
        [hashtable]$Metadata = @{}
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] [$Service] $Message"
    
    # Add metadata if present
    if ($Metadata.Count -gt 0) {
        $metaString = ($Metadata.GetEnumerator() | ForEach-Object { 
            $sanitizedValue = "$($_.Value)" -replace '[\r\n]', ' '
            "$($_.Key)=$sanitizedValue" 
        }) -join ", "
        $logEntry += " | $metaString"
    }
    
    # Write to file
    $logEntry | Out-File -FilePath $script:LogFile -Append -Encoding UTF8
    
    # Console output with colors
    $color = switch ($Level) {
        "SUCCESS" { $script:Colors.Success }
        "ERROR" { $script:Colors.Error }
        "CRITICAL" { $script:Colors.Error }
        "WARNING" { $script:Colors.Warning }
        "DEBUG" { $script:Colors.Debug }
        default { $script:Colors.Info }
    }
    
    if ($VerboseLogging -or $Level -ne "DEBUG") {
        Write-Host $logEntry -ForegroundColor $color
    }
}

function Write-Section {
    param([string]$Title)
    Write-Log "" -Level "INFO"
    Write-Log $("=" * 80) -Level "INFO"
    Write-Log "  $Title" -Level "INFO"
    Write-Log $("=" * 80) -Level "INFO"
    Write-Log "" -Level "INFO"
}

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

function Test-Dependency {
    param(
        [string]$Name,
        [string]$Command,
        [string]$MinimumVersion = $null,
        [string]$Description
    )
    
    Write-Log "Checking dependency: $Name" -Level "DEBUG" -Service "PREFLIGHT"
    
    try {
        $cmd = Get-Command $Command -ErrorAction Stop
        $version = $null
        
        # Try to get version
        try {
            $versionOutput = & $Command --version 2>&1 | Select-Object -First 1
            if ($versionOutput -match '(\d+\.\d+\.\d+)') {
                $version = $matches[1]
            }
        } catch {
            Write-Log "Could not determine version for $Name" -Level "DEBUG" -Service "PREFLIGHT"
        }
        
        if ($MinimumVersion -and $version) {
            $current = [System.Version]$version
            $required = [System.Version]$MinimumVersion
            
            if ($current -lt $required) {
                Write-Log "FAIL: $Name version $version is below minimum $MinimumVersion" -Level "ERROR" -Service "PREFLIGHT"
                return @{ Success = $false; Error = "Version too old: $version < $MinimumVersion" }
            }
        }
        
        Write-Log "PASS: $Name found" -Level "SUCCESS" -Service "PREFLIGHT" -Metadata @{ Version = $version; Path = $cmd.Source }
        return @{ Success = $true; Version = $version; Path = $cmd.Source }
        
    } catch {
        Write-Log "FAIL: $Name not found - $_" -Level "ERROR" -Service "PREFLIGHT"
        return @{ Success = $false; Error = $_.Exception.Message }
    }
}

function Invoke-PreflightChecks {
    Write-Section "PRE-FLIGHT CHECKS"
    
    $results = @{
        Success = $true
        Dependencies = @{}
        Failures = @()
    }
    
    # Check PowerShell version
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -lt 7) {
        Write-Log "CRITICAL: PowerShell 7.0+ required, found $($psVersion.ToString())" -Level "CRITICAL" -Service "PREFLIGHT"
        $results.Success = $false
        $results.Failures += "PowerShell version too old"
    } else {
        Write-Log "PASS: PowerShell $($psVersion.ToString())" -Level "SUCCESS" -Service "PREFLIGHT"
    }
    
    # Check core dependencies
    $dependencies = @(
        @{ Name = "Python"; Command = "python"; MinVersion = "3.12.0"; Description = "Python runtime for backend services" },
        @{ Name = "Node.js"; Command = "node"; MinVersion = "18.0.0"; Description = "Node.js for Cortex frontend" },
        @{ Name = "npm"; Command = "npm"; MinVersion = "9.0.0"; Description = "Node package manager" },
        @{ Name = "Poetry"; Command = "poetry"; MinVersion = "1.7.0"; Description = "Python dependency management" },
        @{ Name = "Docker"; Command = "docker"; MinVersion = "24.0.0"; Description = "Container runtime for infrastructure" },
        @{ Name = "Docker Compose"; Command = "docker-compose"; MinVersion = "2.20.0"; Description = "Multi-container orchestration" }
    )
    
    foreach ($dep in $dependencies) {
        $result = Test-Dependency @dep
        $results.Dependencies[$dep.Name] = $result
        
        if (-not $result.Success) {
            $results.Success = $false
            $results.Failures += "$($dep.Name): $($result.Error)"
        }
    }
    
    # Check environment variables
    Write-Log "Checking environment variables..." -Level "DEBUG" -Service "PREFLIGHT"
    $requiredEnvVars = @(
        "SOMA_INGRESS_KEY",
        "SOMA_PG_DSN",
        "NEO4J_PASSWORD"
    )
    
    foreach ($var in $requiredEnvVars) {
        $value = [Environment]::GetEnvironmentVariable($var)
        if ([string]::IsNullOrEmpty($value)) {
            Write-Log "ERROR: Required environment variable $var not set" -Level "ERROR" -Service "PREFLIGHT"
            $results.Success = $false
            $results.Failures += "Missing environment variable: $var"
        } else {
            # Safe masking that handles short strings
            $masked = if ($value.Length -gt 8) { 
                $value.Substring(0, 4) + "****" + $value.Substring($value.Length - 4)
            } elseif ($value.Length -gt 0) {
                "*" * $value.Length
            } else { 
                "****" 
            }
            Write-Log "PASS: $var is set ($masked)" -Level "SUCCESS" -Service "PREFLIGHT"
        }
    }
    
    # Check project directory structure
    Write-Log "Checking project structure..." -Level "DEBUG" -Service "PREFLIGHT"
    $projectRoot = $PSScriptRoot
    $requiredPaths = @(
        "InGress",
        "InGest",
        "OmegaKG",
        "memOS",
        "Cortex"
    )
    
    foreach ($path in $requiredPaths) {
        $fullPath = Join-Path $projectRoot $path
        if (Test-Path $fullPath) {
            Write-Log "PASS: Directory $path exists" -Level "SUCCESS" -Service "PREFLIGHT"
        } else {
            Write-Log "FAIL: Directory $path not found at $fullPath" -Level "ERROR" -Service "PREFLIGHT"
            $results.Success = $false
            $results.Failures += "Missing directory: $path"
        }
    }
    
    # Summary
    Write-Log "" -Level "INFO"
    if ($results.Success) {
        Write-Log "✓ All pre-flight checks passed" -Level "SUCCESS" -Service "PREFLIGHT"
    } else {
        Write-Log "✗ Pre-flight checks failed:" -Level "ERROR" -Service "PREFLIGHT"
        foreach ($failure in $results.Failures) {
            Write-Log "  - $failure" -Level "ERROR" -Service "PREFLIGHT"
        }
    }
    
    return $results
}

# =============================================================================
# INFRASTRUCTURE MANAGEMENT
# =============================================================================

function Test-Infrastructure {
    param(
        [string]$Name,
        [int]$Port,
        [int]$TimeoutSeconds = 5
    )
    
    Write-Log "Testing $Name on port $Port..." -Level "DEBUG" -Service "INFRA"
    
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $connection = $client.BeginConnect("localhost", $Port, $null, $null)
        $success = $connection.AsyncWaitHandle.WaitOne([TimeSpan]::FromSeconds($TimeoutSeconds))
        
        if ($success -and $client.Connected) {
            Write-Log "PASS: $Name is available on port $Port" -Level "SUCCESS" -Service "INFRA"
            return $true
        } else {
            Write-Log "FAIL: $Name not responding on port $Port" -Level "WARNING" -Service "INFRA"
            return $false
        }
    } catch {
        Write-Log "FAIL: $Name connection error - $_" -Level "WARNING" -Service "INFRA"
        return $false
    } finally {
        if ($null -ne $client) {
            $client.Close()
            $client.Dispose()
        }
    }
}

function Start-Infrastructure {
    Write-Section "INFRASTRUCTURE STARTUP"
    
    # Check if Docker is running
    try {
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Docker not running"
        }
        Write-Log "Docker is running" -Level "SUCCESS" -Service "INFRA"
    } catch {
        Write-Log "CRITICAL: Docker is not running. Please start Docker Desktop." -Level "CRITICAL" -Service "INFRA"
        throw "Docker not available"
    }
    
    # Check if infrastructure is already running
    $allRunning = $true
    foreach ($infra in $script:Infrastructure) {
        if (-not (Test-Infrastructure -Name $infra.Name -Port $infra.Port)) {
            $allRunning = $false
            break
        }
    }
    
    if ($allRunning) {
        Write-Log "All infrastructure services already running" -Level "SUCCESS" -Service "INFRA"
        return $true
    }
    
    if ($SkipDocker) {
        Write-Log "WARNING: Infrastructure not running but --SkipDocker specified" -Level "WARNING" -Service "INFRA"
        Write-Log "Please ensure PostgreSQL, Neo4j, and Redis are running manually" -Level "WARNING" -Service "INFRA"
        return $false
    }
    
    # Start infrastructure containers
    Write-Log "Starting infrastructure containers..." -Level "INFO" -Service "INFRA"
    
    $dockerComposeFile = Join-Path $PSScriptRoot "docker-compose.yml"
    if (-not (Test-Path $dockerComposeFile)) {
        $dockerComposeFile = Join-Path $PSScriptRoot "docker-compose.yaml"
    }
    
    if (Test-Path $dockerComposeFile) {
        Write-Log "Using docker-compose: $dockerComposeFile" -Level "DEBUG" -Service "INFRA"
        
        try {
            # Use modern docker compose (V2) command
            docker compose -f $dockerComposeFile up -d 2>&1 | ForEach-Object {
                Write-Log $_ -Level "DEBUG" -Service "INFRA"
            }
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Infrastructure containers started successfully" -Level "SUCCESS" -Service "INFRA"
            } else {
                throw "docker compose failed with exit code $LASTEXITCODE"
            }
        } catch {
            Write-Log "ERROR: Failed to start infrastructure - $_" -Level "ERROR" -Service "INFRA"
            return $false
        }
    } else {
        Write-Log "WARNING: No docker-compose.yml found, assuming manual infrastructure setup" -Level "WARNING" -Service "INFRA"
    }
    
    # Wait for infrastructure to be ready
    Write-Log "Waiting for infrastructure to be ready..." -Level "INFO" -Service "INFRA"
    $maxWaitSeconds = 60
    $waited = 0
    
    while ($waited -lt $maxWaitSeconds) {
        $allReady = $true
        foreach ($infra in $script:Infrastructure) {
            if (-not (Test-Infrastructure -Name $infra.Name -Port $infra.Port -TimeoutSeconds 2)) {
                $allReady = $false
                break
            }
        }
        
        if ($allReady) {
            Write-Log "All infrastructure services are ready" -Level "SUCCESS" -Service "INFRA"
            return $true
        }
        
        Write-Log "Waiting for infrastructure... ($waited/$maxWaitSeconds seconds)" -Level "DEBUG" -Service "INFRA"
        Start-Sleep -Seconds 2
        $waited += 2
    }
    
    Write-Log "TIMEOUT: Infrastructure failed to start within $maxWaitSeconds seconds" -Level "ERROR" -Service "INFRA"
    return $false
}

# =============================================================================
# SERVICE HEALTH CHECKS WITH EXPONENTIAL BACKOFF
# =============================================================================

function Test-ServiceHealth {
    param(
        [hashtable]$Service,
        [int]$MaxRetries = $script:MaxRetries,
        [int]$InitialBackoff = $script:InitialBackoffSeconds
    )
    
    $serviceName = $Service.Name
    $port = $Service.Port
    $endpoint = $Service.HealthEndpoint
    $url = "http://localhost:$port$endpoint"
    
    Write-Log "Health check for $serviceName at $url" -Level "DEBUG" -Service $serviceName
    
    $retryCount = 0
    $backoff = $InitialBackoff
    
    while ($retryCount -lt $MaxRetries) {
        try {
            $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
            
            if ($response.StatusCode -eq 200) {
                Write-Log "✓ $serviceName is healthy" -Level "SUCCESS" -Service $serviceName -Metadata @{ 
                    StatusCode = $response.StatusCode
                    Retry = $retryCount 
                }
                return @{ Success = $true; StatusCode = $response.StatusCode; Retries = $retryCount }
            } else {
                Write-Log "⚠ $serviceName returned status $($response.StatusCode)" -Level "WARNING" -Service $serviceName
            }
        } catch {
            $errorMsg = $_.Exception.Message
            Write-Log "✗ $serviceName health check failed (attempt $($retryCount + 1)/$MaxRetries): $errorMsg" -Level "DEBUG" -Service $serviceName
        }
        
        $retryCount++
        if ($retryCount -lt $MaxRetries) {
            Write-Log "Waiting ${backoff}s before retry..." -Level "DEBUG" -Service $serviceName
            Start-Sleep -Seconds $backoff
            $backoff = [Math]::Min($backoff * 2, 30)  # Exponential backoff, max 30s
        }
    }
    
    Write-Log "✗ $serviceName health check failed after $MaxRetries attempts" -Level "ERROR" -Service $serviceName
    return @{ Success = $false; Retries = $retryCount }
}

function Start-Services {
    Write-Section "SERVICE STARTUP"
    
    $results = @{
        Success = $true
        Services = @{}
    }
    
    foreach ($service in $script:Services) {
        $serviceName = $service.Name
        Write-Log "Starting $serviceName ($($service.Code))..." -Level "INFO" -Service $serviceName
        
        # Check if service is already running on its port (more reliable than process name)
        if (Test-Infrastructure -Name $serviceName -Port $service.Port -TimeoutSeconds 2) {
            Write-Log "$serviceName is already running on port $($service.Port)" -Level "SUCCESS" -Service $serviceName
        } else {
            # Start the service
            $started = Start-ServiceProcess -Service $service
            if (-not $started) {
                if ($service.Required) {
                    Write-Log "CRITICAL: Required service $serviceName failed to start" -Level "CRITICAL" -Service $serviceName
                    $results.Success = $false
                    $results.Services[$serviceName] = @{ Success = $false; Error = "Failed to start" }
                    continue
                } else {
                    Write-Log "WARNING: Optional service $serviceName failed to start" -Level "WARNING" -Service $serviceName
                }
            }
        }
        
        # Wait for startup delay
        Write-Log "Waiting $($service.StartupDelay)s for $serviceName to initialize..." -Level "DEBUG" -Service $serviceName
        Start-Sleep -Seconds $service.StartupDelay
        
        # Health check with exponential backoff
        $health = Test-ServiceHealth -Service $service -MaxRetries $MaxRetries -InitialBackoff $InitialBackoffSeconds
        $results.Services[$serviceName] = $health
        
        if (-not $health.Success -and $service.Required) {
            Write-Log "CRITICAL: Required service $serviceName is not healthy" -Level "CRITICAL" -Service $serviceName
            $results.Success = $false
        }
    }
    
    return $results
}

function Start-ServiceProcess {
    param([hashtable]$Service)
    
    $serviceName = $Service.Name
    $projectRoot = $PSScriptRoot
    
    try {
        switch ($serviceName) {
            "Senses" {
                $workingDir = Join-Path $projectRoot "InGress"
                if ([string]::IsNullOrEmpty($env:SOMA_INGRESS_KEY)) {
                    throw "SOMA_INGRESS_KEY environment variable is required but not set"
                }
                # Use cmd.exe to inherit environment properly
                $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python -m soma_ingress.main" -WorkingDirectory $workingDir -WindowStyle Hidden -PassThru
            }
            "Stomach" {
                $workingDir = Join-Path $projectRoot "InGest"
                $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "poetry run python -m ingest_llm_as.main" -WorkingDirectory $workingDir -WindowStyle Hidden -PassThru
            }
            "Brain" {
                $workingDir = Join-Path $projectRoot "OmegaKG"
                $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "poetry run python -m omega_kg.main" -WorkingDirectory $workingDir -WindowStyle Hidden -PassThru
            }
            "Bridge" {
                $workingDir = Join-Path $projectRoot "memOS"
                $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "poetry run python -m memos_mcp" -WorkingDirectory $workingDir -WindowStyle Hidden -PassThru
            }
            "Cortex" {
                $workingDir = Join-Path $projectRoot "Cortex"
                $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory $workingDir -WindowStyle Hidden -PassThru
            }
        }
        
        if ($null -eq $proc) {
            throw "Failed to start process - Start-Process returned null"
        }
        
        # Wait briefly and verify process didn't crash immediately
        Start-Sleep -Milliseconds 500
        if ($proc.HasExited) {
            throw "Process exited immediately with code $($proc.ExitCode)"
        }
        
        Write-Log "$serviceName process started (PID: $($proc.Id))" -Level "SUCCESS" -Service $serviceName
        return $true
        
    } catch {
        Write-Log "Failed to start $serviceName - $_" -Level "ERROR" -Service $serviceName
        return $false
    }
}

# =============================================================================
# BROWSER LAUNCH
# =============================================================================

function Open-CortexDashboard {
    param([int]$Port = 6001)
    
    if ($NoBrowser) {
        Write-Log "Browser launch skipped (--NoBrowser specified)" -Level "INFO" -Service "LAUNCH"
        return
    }
    
    $url = "http://localhost:$Port"
    Write-Log "Opening Cortex Dashboard at $url" -Level "INFO" -Service "LAUNCH"
    
    try {
        Start-Process $url
        Write-Log "✓ Browser launched successfully" -Level "SUCCESS" -Service "LAUNCH"
    } catch {
        Write-Log "✗ Failed to launch browser - $_" -Level "ERROR" -Service "LAUNCH"
        Write-Log "Please manually navigate to $url" -Level "INFO" -Service "LAUNCH"
    }
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

function Show-Banner {
    $banner = @"

    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║   ███████╗ ██████╗ ███╗   ███╗ █████╗     ███████╗ ██████╗      ║
    ║   ██╔════╝██╔═══██╗████╗ ████║██╔══██╗    ██╔════╝██╔═══██╗     ║
    ║   ███████╗██║   ██║██╔████╔██║███████║    █████╗  ██║   ██║     ║
    ║   ╚════██║██║   ██║██║╚██╔╝██║██╔══██║    ██╔══╝  ██║   ██║     ║
    ║   ███████║╚██████╔╝██║ ╚═╝ ██║██║  ██║    ███████╗╚██████╔╝     ║
    ║   ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝    ╚══════╝ ╚═════╝      ║
    ║                                                                  ║
    ║              ECOSYSTEM STARTUP v$script:Version                         ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝

"@
    Write-Host $banner -ForegroundColor Cyan
    Write-Log "Soma Ecosystem Startup v$script:Version" -Level "INFO"
    Write-Log "Log file: $script:LogFile" -Level "INFO"
}

function Show-Summary {
    param(
        [bool]$Success,
        [hashtable]$ServiceResults,
        [TimeSpan]$Duration
    )
    
    Write-Section "STARTUP SUMMARY"
    
    if ($Success) {
        Write-Log "✓ SOMA ECOSYSTEM IS OPERATIONAL" -Level "SUCCESS"
        Write-Log "  All services are healthy and ready" -Level "SUCCESS"
    } else {
        Write-Log "✗ SOMA ECOSYSTEM STARTUP FAILED" -Level "ERROR"
        Write-Log "  Some services failed to start or are unhealthy" -Level "ERROR"
    }
    
    Write-Log "" -Level "INFO"
    Write-Log "Service Status:" -Level "INFO"
    foreach ($service in $script:Services) {
        $name = $service.Name
        $result = $ServiceResults[$name]
        $status = if ($result.Success) { "✓ HEALTHY" } else { "✗ FAILED" }
        $retries = if ($result.Retries -gt 0) { "($($result.Retries) retries)" } else { "" }
        Write-Log "  $name $status $retries" -Level $(if ($result.Success) { "SUCCESS" } else { "ERROR" })
    }
    
    Write-Log "" -Level "INFO"
    Write-Log "Duration: $($Duration.ToString('mm\:ss\.fff'))" -Level "INFO"
    Write-Log "Log file: $script:LogFile" -Level "INFO"
    
    if ($Success) {
        Write-Log "" -Level "INFO"
        Write-Log "🧠 Cortex Dashboard: http://localhost:6001" -Level "SUCCESS"
        Write-Log "" -Level "INFO"
    }
}

# Main execution
try {
    Show-Banner
    Initialize-Logging -LogDirectory $LogPath
    
    # Pre-flight checks
    if (-not $SkipPreflight) {
        $preflight = Invoke-PreflightChecks
        if (-not $preflight.Success) {
            Write-Log "Pre-flight checks failed. Use -SkipPreflight to bypass (not recommended)." -Level "ERROR"
            exit 1
        }
    } else {
        Write-Log "WARNING: Pre-flight checks skipped" -Level "WARNING"
    }
    
    # Start infrastructure
    $infraReady = Start-Infrastructure
    if (-not $infraReady) {
        Write-Log "Infrastructure not ready. Cannot continue." -Level "CRITICAL"
        exit 1
    }
    
    # Start services
    $serviceResults = Start-Services
    
    # Calculate duration
    $endTime = Get-Date
    $duration = $endTime - $script:StartTime
    
    # Show summary
    Show-Summary -Success $serviceResults.Success -ServiceResults $serviceResults.Services -Duration $duration
    
    # Open browser if successful
    if ($serviceResults.Success) {
        Open-CortexDashboard
        Write-Log "🚀 Soma Ecosystem is ready for operation!" -Level "SUCCESS"
        exit 0
    } else {
        Write-Log "💥 Startup failed. Check logs at $script:LogFile" -Level "ERROR"
        exit 1
    }
    
} catch {
    Write-Log "FATAL ERROR: $_" -Level "CRITICAL"
    Write-Log "Stack Trace: $($_.ScriptStackTrace)" -Level "DEBUG"
    exit 1
}
