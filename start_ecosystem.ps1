<#
.SYNOPSIS
    Soma Ecosystem Orchestrator - Robust Windows 11 Service Launcher
    
.DESCRIPTION
    Launches the complete Soma biomorphic knowledge ecosystem with:
    - Exponential backoff retry logic
    - Decoupled service management (failures don't cascade)
    - Comprehensive verbose logging for debugging
    - Health monitoring and automatic recovery
    - Cortex dashboard telemetry integration
    - Windows 11 optimized PowerShell syntax
    
.PARAMETER ShowConsole
    Show service console windows (for debugging)
    
.PARAMETER SkipMigrations
    Skip database migrations
    
.PARAMETER SkipContracts
    Skip API contract validation
    
.PARAMETER Persistent
    Run watchdog loop with automatic service recovery
    
.PARAMETER LogLevel
    Logging verbosity: Debug, Info, Warning, Error (default: Info)
    
.EXAMPLE
    .\start_ecosystem.ps1
    Standard startup with hidden consoles
    
.EXAMPLE
    .\start_ecosystem.ps1 -ShowConsole -LogLevel Debug
    Debug mode with visible windows and verbose logging
    
.EXAMPLE
    .\start_ecosystem.ps1 -Persistent
    Production mode with continuous health monitoring and auto-recovery
#>

[CmdletBinding()]
param(
    [switch]$ShowConsole,
    [switch]$SkipMigrations,
    [switch]$SkipContracts,
    [switch]$Persistent,
    [ValidateSet('Debug', 'Info', 'Warning', 'Error')]
    [string]$LogLevel = 'Info'
)

# ============================================================================
# CONFIGURATION & INITIALIZATION
# ============================================================================

$ErrorActionPreference = 'Continue'  # Don't stop on errors - we handle them explicitly
$Script:StartTime = Get-Date
$Script:LogDir = Join-Path $PSScriptRoot "logs"
$Script:LogFile = Join-Path $Script:LogDir "startup_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Ensure Poetry is in PATH (Common Windows Locations)
$PoetryPaths = @(
    "$env:APPDATA\Python\Scripts",
    "$env:APPDATA\pypoetry\venv\Scripts"
)
foreach ($Path in $PoetryPaths) {
    if ((Test-Path $Path) -and ($env:PATH -notlike "*$Path*")) {
        $env:PATH = "$Path;$env:PATH"
        Write-Host "Added $Path to PATH" -ForegroundColor DarkGray
    }
}

$Script:ServiceProcesses = @{}  # Track all service processes
$Script:ServiceHealth = @{}  # Track service health status
$Script:FailedServices = @()  # Track failed services
$Script:LogLevelValue = @{
    'Debug'   = 0
    'Info'    = 1
    'Warning' = 2
    'Error'   = 3
}[$LogLevel]

# Service configuration with dependencies and retry settings
$Script:Services = @{
    'Docker-Postgres' = @{
        Type        = 'Docker'
        Port        = 5432
        HealthCheck = { Test-DatabaseConnection -Port 5432 }
        Command     = 'docker compose up -d'
        Priority    = 1
        MaxRetries  = 5
        BaseDelay   = 2
    }
    'Docker-Neo4j'    = @{
        Type        = 'Docker'
        Port        = 7687
        HealthCheck = { Test-Port -Port 7687 }
        Command     = 'docker compose up -d'
        Priority    = 1
        MaxRetries  = 5
        BaseDelay   = 2
    }
    'Docker-Redis'    = @{
        Type        = 'Docker'
        Port        = 6380
        HealthCheck = { Test-Port -Port 6380 }
        Command     = 'docker compose up -d'
        Priority    = 1
        MaxRetries  = 5
        BaseDelay   = 2
    }
    'InGress'         = @{
        Type           = 'Python'
        Port           = 8000
        Path           = 'InGress'
        Command        = 'poetry run python -m soma_ingress.main'
        HealthEndpoint = 'http://localhost:8000/health'
        Priority       = 2
        MaxRetries     = 10
        BaseDelay      = 3
        DependsOn      = @('Docker-Postgres', 'Docker-Redis')
    }
    'InGest'          = @{
        Type           = 'Python'
        Port           = 8766
        Path           = 'InGest'
        Command        = 'poetry run python -m ingest_llm_as.main'
        HealthEndpoint = 'http://localhost:8766/health'
        Priority       = 3
        MaxRetries     = 10
        BaseDelay      = 3
        DependsOn      = @('Docker-Postgres', 'Docker-Redis', 'InGress')
    }
    'OmegaKG'         = @{
        Type           = 'Python'
        Port           = 8765
        Path           = 'OmegaKG'
        Command        = 'poetry run python -m omega_kg.main'
        HealthEndpoint = 'http://localhost:8765/health'
        Priority       = 3
        MaxRetries     = 10
        BaseDelay      = 3
        DependsOn      = @('Docker-Postgres', 'Docker-Neo4j', 'Docker-Redis')
    }
    'memOS'           = @{
        Type           = 'Python'
        Port           = 8768
        Path           = 'memOS'
        Command        = 'poetry run python -m memos_mcp.server --sse'
        HealthEndpoint = 'http://localhost:8768/health'
        Priority       = 4
        MaxRetries     = 10
        BaseDelay      = 3
        DependsOn      = @('Docker-Postgres', 'OmegaKG')
    }
    'Cortex'          = @{
        Type           = 'Node'
        Port           = 6001
        Path           = 'Cortex'
        Command        = 'npm run dev'
        HealthEndpoint = 'http://localhost:6001'
        Priority       = 5
        MaxRetries     = 8
        BaseDelay      = 2
        DependsOn      = @('InGress', 'InGest', 'OmegaKG', 'memOS')
    }
}

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

function Write-Log {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        
        [ValidateSet('Debug', 'Info', 'Warning', 'Error', 'Success')]
        [string]$Level = 'Info',
        
        [string]$Service = 'System'
    )
    
    $LevelValue = @{
        'Debug'   = 0
        'Info'    = 1
        'Warning' = 2
        'Error'   = 3
        'Success' = 1
    }[$Level]
    
    if ($LevelValue -lt $Script:LogLevelValue) {
        return  # Skip if below threshold
    }
    
    $Timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
    $LogLine = "[$Timestamp] [$Level] [$Service] $Message"
    
    # Ensure log directory exists
    if (-not (Test-Path $Script:LogDir)) {
        New-Item -ItemType Directory -Path $Script:LogDir -Force | Out-Null
    }
    
    # Write to file
    Add-Content -Path $Script:LogFile -Value $LogLine -Encoding UTF8
    
    # Console output with colors
    $Color = switch ($Level) {
        'Debug' { 'Gray' }
        'Info' { 'White' }
        'Success' { 'Green' }
        'Warning' { 'Yellow' }
        'Error' { 'Red' }
    }
    
    Write-Host $LogLine -ForegroundColor $Color
}

function Write-Banner {
    param([string]$Text)
    
    $Banner = @"

╔═══════════════════════════════════════════════════════════════════════╗
║  $($Text.PadRight(67))  ║
╚═══════════════════════════════════════════════════════════════════════╝

"@
    Write-Log -Message "`n$Banner" -Level Info
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Test-Port {
    param(
        [int]$Port,
        [string]$Hostname = 'localhost',
        [int]$TimeoutMs = 1000
    )
    
    try {
        # Force IPv4 to avoid IPv6 connection issues with 127.0.0.1 bindings
        $TcpClient = New-Object System.Net.Sockets.TcpClient([System.Net.Sockets.AddressFamily]::InterNetwork)
        $AsyncResult = $TcpClient.BeginConnect($Hostname, $Port, $null, $null)
        $Wait = $AsyncResult.AsyncWaitHandle.WaitOne($TimeoutMs)
        
        if ($Wait) {
            $TcpClient.EndConnect($AsyncResult)
            $TcpClient.Close()
            return $true
        }
        else {
            $TcpClient.Close()
            return $false
        }
    }
    catch {
        return $false
    }
}

function Test-DatabaseConnection {
    param([int]$Port = 5432)
    
    try {
        $PgIsReady = Get-Command pg_isready -ErrorAction SilentlyContinue
        if ($PgIsReady) {
            $Result = pg_isready -h localhost -p $Port 2>&1
            return $LASTEXITCODE -eq 0
        }
        else {
            # Fallback to TCP test
            return Test-Port -Port $Port
        }
    }
    catch {
        return $false
    }
}

function Test-HttpEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSec = 5
    )
    
    try {
        $Response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return $Response.StatusCode -eq 200
    }
    catch {
        Write-Log -Message "HTTP check failed: $_" -Level Debug
        return $false
    }
}

function Get-ExponentialDelay {
    param(
        [int]$Attempt,
        [int]$BaseDelay = 2,
        [int]$MaxDelay = 60
    )
    
    $Delay = [Math]::Min($BaseDelay * [Math]::Pow(2, $Attempt), $MaxDelay)
    $Jitter = Get-Random -Minimum 0 -Maximum ($Delay * 0.1)  # Add 10% jitter
    return [int]($Delay + $Jitter)
}

function Wait-ForDependencies {
    param(
        [string]$ServiceName,
        [hashtable]$Service
    )
    
    if (-not $Service.DependsOn) {
        return $true
    }
    
    Write-Log -Message "Checking dependencies: $($Service.DependsOn -join ', ')" -Level Debug -Service $ServiceName
    
    foreach ($Dependency in $Service.DependsOn) {
        if ($Script:ServiceHealth[$Dependency] -ne 'Healthy') {
            Write-Log -Message "Dependency $Dependency not healthy (Status: $($Script:ServiceHealth[$Dependency]))" -Level Warning -Service $ServiceName
            return $false
        }
    }
    
    return $true
}

# ============================================================================
# SERVICE MANAGEMENT FUNCTIONS
# ============================================================================

function Start-DockerServices {
    Write-Banner "STARTING DOCKER INFRASTRUCTURE"
    
    # Check if containers are already running
    Write-Log -Message "Checking for existing Docker containers..." -Level Info
    $ExistingContainers = docker ps --filter "name=postgres" --filter "name=neo4j" --filter "name=redis" --format "{{.Names}}" 2>&1
    
    if ($ExistingContainers -and $ExistingContainers.Count -ge 3) {
        Write-Log -Message "Docker containers already running, skipping docker compose up" -Level Info
    }
    else {
        Write-Log -Message "Starting Docker Compose services..." -Level Info
    
        try {
            $DockerComposeFile = Join-Path $PSScriptRoot "docker-compose.yml"
            if (-not (Test-Path $DockerComposeFile)) {
                Write-Log -Message "docker-compose.yml not found at $DockerComposeFile" -Level Error
                return $false
            }
            
            # Run docker compose with timeout (30 seconds)
            Write-Log -Message "Running: docker compose up -d (timeout: 30s)" -Level Debug
            
            $Job = Start-Job -ScriptBlock {
                docker compose up -d 2>&1
                return $LASTEXITCODE
            } -WorkingDirectory $PSScriptRoot
            
            $Completed = Wait-Job -Job $Job -Timeout 30
            
            if (-not $Completed) {
                Write-Log -Message "Docker Compose timed out after 30 seconds - containers may already be running" -Level Warning
                Stop-Job -Job $Job
                Remove-Job -Job $Job
                
                # Check if containers are actually running
                $Running = docker ps --filter "name=postgres" --filter "name=neo4j" --filter "name=redis" --format "{{.Names}}" 2>&1
                if ($Running) {
                    Write-Log -Message "Docker containers detected as running, continuing..." -Level Info
                }
                else {
                    Write-Log -Message "No Docker containers detected. Please start Docker manually: docker compose up -d" -Level Error
                    return $false
                }
            }
            else {
                $Result = Receive-Job -Job $Job
                $ExitCode = Receive-Job -Job $Job -Keep | Select-Object -Last 1
                Remove-Job -Job $Job
                
                if ($ExitCode -ne 0 -and $ExitCode -ne $null) {
                    Write-Log -Message "Docker Compose failed with exit code $ExitCode`: $Result" -Level Error
                    return $false
                }
                
                Write-Log -Message "Docker Compose started successfully" -Level Success
            }
        }
        catch {
            Write-Log -Message "Docker startup exception: $_" -Level Error
            return $false
        }
    }
    
    # Wait for each Docker service with exponential backoff
    foreach ($ServiceName in @('Docker-Postgres', 'Docker-Neo4j', 'Docker-Redis')) {
        $Service = $Script:Services[$ServiceName]
        $Healthy = Wait-ForService -ServiceName $ServiceName -Service $Service
        
        if (-not $Healthy) {
            Write-Log -Message "$ServiceName failed to become healthy" -Level Error
            $Script:FailedServices += $ServiceName
            $Script:ServiceHealth[$ServiceName] = 'Failed'
        }
        else {
            $Script:ServiceHealth[$ServiceName] = 'Healthy'
            Write-Log -Message "$ServiceName is healthy" -Level Success -Service $ServiceName
        }
    }
    
    return $true
}

function Wait-ForService {
    param(
        [string]$ServiceName,
        [hashtable]$Service
    )
    
    $MaxRetries = $Service.MaxRetries
    $BaseDelay = $Service.BaseDelay
    
    Write-Log -Message "Waiting for $ServiceName (Port: $($Service.Port))..." -Level Info -Service $ServiceName
    
    for ($Attempt = 0; $Attempt -lt $MaxRetries; $Attempt++) {
        Write-Log -Message "Health check attempt $($Attempt + 1)/$MaxRetries" -Level Debug -Service $ServiceName
        
        $IsHealthy = $false
        
        try {
            if ($Service.HealthEndpoint) {
                $IsHealthy = Test-HttpEndpoint -Url $Service.HealthEndpoint
            }
            elseif ($Service.HealthCheck) {
                $IsHealthy = & $Service.HealthCheck
            }
            else {
                $IsHealthy = Test-Port -Port $Service.Port
            }
            
            if ($IsHealthy) {
                Write-Log -Message "$ServiceName health check PASSED" -Level Success -Service $ServiceName
                return $true
            }
        }
        catch {
            Write-Log -Message "Health check error: $_" -Level Debug -Service $ServiceName
        }
        
        if ($Attempt -lt $MaxRetries - 1) {
            $Delay = Get-ExponentialDelay -Attempt $Attempt -BaseDelay $BaseDelay
            Write-Log -Message "Health check failed. Retrying in $Delay seconds..." -Level Debug -Service $ServiceName
            Start-Sleep -Seconds $Delay
        }
    }
    
    Write-Log -Message "$ServiceName health check FAILED after $MaxRetries attempts" -Level Error -Service $ServiceName
    return $false
}

function Start-PythonService {
    param(
        [string]$ServiceName,
        [hashtable]$Service
    )
    
    Write-Log -Message "Starting Python service..." -Level Info -Service $ServiceName
    
    # Check dependencies
    if (-not (Wait-ForDependencies -ServiceName $ServiceName -Service $Service)) {
        Write-Log -Message "Dependencies not met, skipping startup" -Level Warning -Service $ServiceName
        return $null
    }
    
    $ServicePath = Join-Path $PSScriptRoot $Service.Path
    if (-not (Test-Path $ServicePath)) {
        Write-Log -Message "Service path not found: $ServicePath" -Level Error -Service $ServiceName
        return $null
    }
    
    # Check Poetry installation
    $PoetryEnv = Join-Path $ServicePath ".venv"
    if (-not (Test-Path $PoetryEnv)) {
        Write-Log -Message "Poetry environment not found at $PoetryEnv. Run 'poetry install' first." -Level Error -Service $ServiceName
        return $null
    }
    
    # Load .env file if it exists
    $EnvFile = Join-Path $ServicePath ".env"
    if (Test-Path $EnvFile) {
        Write-Log -Message "Loading environment from .env file" -Level Debug -Service $ServiceName
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
                Write-Log -Message "Loaded env var: $key" -Level Debug -Service $ServiceName
            }
        }
    }
    else {
        Write-Log -Message ".env file not found at $EnvFile" -Level Warning -Service $ServiceName
    }
    
    try {
        $LogFile = Join-Path $Script:LogDir "$ServiceName.log"
        
        $ProcessParams = @{
            FilePath               = 'poetry'
            ArgumentList           = $Service.Command.Replace('poetry ', '').Split(' ')
            WorkingDirectory       = $ServicePath
            RedirectStandardOutput = $LogFile
            RedirectStandardError  = Join-Path $Script:LogDir "$ServiceName.error.log"
            NoNewWindow            = -not $ShowConsole
            PassThru               = $true
        }
        
        Write-Log -Message "Command: $($Service.Command)" -Level Debug -Service $ServiceName
        Write-Log -Message "Working directory: $ServicePath" -Level Debug -Service $ServiceName
        
        $Process = Start-Process @ProcessParams
        
        if ($Process) {
            Write-Log -Message "Process started (PID: $($Process.Id))" -Level Success -Service $ServiceName
            $Script:ServiceProcesses[$ServiceName] = $Process
            
            # Wait for service to become healthy
            $Healthy = Wait-ForService -ServiceName $ServiceName -Service $Service
            
            if ($Healthy) {
                $Script:ServiceHealth[$ServiceName] = 'Healthy'
                return $Process
            }
            else {
                Write-Log -Message "Service started but failed health checks" -Level Error -Service $ServiceName
                $Script:ServiceHealth[$ServiceName] = 'Unhealthy'
                $Script:FailedServices += $ServiceName
                return $null
            }
        }
        else {
            Write-Log -Message "Failed to start process" -Level Error -Service $ServiceName
            return $null
        }
    }
    catch {
        Write-Log -Message "Exception during startup: $_" -Level Error -Service $ServiceName
        Write-Log -Message "Stack trace: $($_.ScriptStackTrace)" -Level Debug -Service $ServiceName
        return $null
    }
}

function Start-NodeService {
    param(
        [string]$ServiceName,
        [hashtable]$Service
    )
    
    Write-Log -Message "Starting Node service..." -Level Info -Service $ServiceName
    
    # Check dependencies
    if (-not (Wait-ForDependencies -ServiceName $ServiceName -Service $Service)) {
        Write-Log -Message "Dependencies not met, skipping startup" -Level Warning -Service $ServiceName
        return $null
    }
    
    $ServicePath = Join-Path $PSScriptRoot $Service.Path
    if (-not (Test-Path $ServicePath)) {
        Write-Log -Message "Service path not found: $ServicePath" -Level Error -Service $ServiceName
        return $null
    }
    
    # Check node_modules
    $NodeModules = Join-Path $ServicePath "node_modules"
    if (-not (Test-Path $NodeModules)) {
        Write-Log -Message "node_modules not found. Running npm install..." -Level Warning -Service $ServiceName
        Push-Location $ServicePath
        npm install 2>&1 | Out-File (Join-Path $Script:LogDir "$ServiceName.install.log")
        Pop-Location
    }
    
    try {
        $LogFile = Join-Path $Script:LogDir "$ServiceName.log"
        
        $ProcessParams = @{
            FilePath               = 'npm.cmd'
            ArgumentList           = 'run', 'dev'
            WorkingDirectory       = $ServicePath
            RedirectStandardOutput = $LogFile
            RedirectStandardError  = Join-Path $Script:LogDir "$ServiceName.error.log"
            NoNewWindow            = -not $ShowConsole
            PassThru               = $true
        }
        
        Write-Log -Message "Command: npm run dev" -Level Debug -Service $ServiceName
        Write-Log -Message "Working directory: $ServicePath" -Level Debug -Service $ServiceName
        
        $Process = Start-Process @ProcessParams
        
        if ($Process) {
            Write-Log -Message "Process started (PID: $($Process.Id))" -Level Success -Service $ServiceName
            $Script:ServiceProcesses[$ServiceName] = $Process
            
            # Wait for service to become healthy
            $Healthy = Wait-ForService -ServiceName $ServiceName -Service $Service
            
            if ($Healthy) {
                $Script:ServiceHealth[$ServiceName] = 'Healthy'
                return $Process
            }
            else {
                Write-Log -Message "Service started but failed health checks" -Level Error -Service $ServiceName
                $Script:ServiceHealth[$ServiceName] = 'Unhealthy'
                $Script:FailedServices += $ServiceName
                return $null
            }
        }
        else {
            Write-Log -Message "Failed to start process" -Level Error -Service $ServiceName
            return $null
        }
    }
    catch {
        Write-Log -Message "Exception during startup: $_" -Level Error -Service $ServiceName
        Write-Log -Message "Stack trace: $($_.ScriptStackTrace)" -Level Debug -Service $ServiceName
        return $null
    }
}

# ============================================================================
# MAINTENANCE FUNCTIONS
# ============================================================================

function Invoke-Migrations {
    if ($SkipMigrations) {
        Write-Log -Message "Skipping migrations (--SkipMigrations flag)" -Level Info
        return $true
    }
    
    Write-Banner "RUNNING DATABASE MIGRATIONS"
    
    $MigrationScript = Join-Path $PSScriptRoot "scripts\database\migrate_all.py"
    if (-not (Test-Path $MigrationScript)) {
        Write-Log -Message "Migration script not found: $MigrationScript" -Level Warning
        return $true  # Non-fatal
    }
    
    try {
        Write-Log -Message "Running migrate_all.py upgrade..." -Level Info
        
        # Set environment variables for migrations
        $env:REQUESTS_CA_BUNDLE = & poetry run python -c "import certifi; print(certifi.where())" 2>$null
        
        $Result = poetry run python $MigrationScript upgrade 2>&1
        $Success = $LASTEXITCODE -eq 0
        
        if ($Success) {
            Write-Log -Message "Migrations completed successfully" -Level Success
        }
        else {
            Write-Log -Message "Migrations failed: $Result" -Level Error
        }
        
        return $Success
    }
    catch {
        Write-Log -Message "Migration exception: $_" -Level Error
        return $false
    }
}

function Invoke-ContractValidation {
    if ($SkipContracts) {
        Write-Log -Message "Skipping contract validation (--SkipContracts flag)" -Level Info
        return $true
    }
    
    Write-Banner "VALIDATING API CONTRACTS"
    
    $ContractScript = Join-Path $PSScriptRoot "contracts\validate_contracts.py"
    if (-not (Test-Path $ContractScript)) {
        Write-Log -Message "Contract validation script not found: $ContractScript" -Level Warning
        return $true  # Non-fatal
    }
    
    try {
        Write-Log -Message "Running validate_contracts.py..." -Level Info
        
        $Result = poetry run python $ContractScript 2>&1
        $Success = $LASTEXITCODE -eq 0
        
        if ($Success) {
            Write-Log -Message "Contract validation passed" -Level Success
        }
        else {
            Write-Log -Message "Contract validation failed: $Result" -Level Warning
        }
        
        return $Success
    }
    catch {
        Write-Log -Message "Contract validation exception: $_" -Level Error
        return $false
    }
}

# ============================================================================
# MONITORING & RECOVERY
# ============================================================================

function Test-ServiceHealth {
    param([string]$ServiceName)
    
    $Service = $Script:Services[$ServiceName]
    
    # Check process is still running
    if ($Script:ServiceProcesses.ContainsKey($ServiceName)) {
        $Process = $Script:ServiceProcesses[$ServiceName]
        if ($Process.HasExited) {
            Write-Log -Message "Process has exited (Exit code: $($Process.ExitCode))" -Level Error -Service $ServiceName
            return $false
        }
    }
    
    # Check health endpoint
    if ($Service.HealthEndpoint) {
        return Test-HttpEndpoint -Url $Service.HealthEndpoint -TimeoutSec 3
    }
    elseif ($Service.Port) {
        return Test-Port -Port $Service.Port
    }
    
    return $false
}

function Start-WatchdogLoop {
    Write-Banner "STARTING WATCHDOG MONITORING"
    
    Write-Log -Message "Watchdog will monitor and recover failed services" -Level Info
    Write-Log -Message "Press Ctrl+C to stop" -Level Info
    
    $CheckInterval = 30  # seconds
    $RestartAttempts = @{}  # Track restart attempts per service
    
    try {
        while ($true) {
            Start-Sleep -Seconds $CheckInterval
            
            Write-Log -Message "Performing health checks..." -Level Debug
            
            foreach ($ServiceName in $Script:ServiceProcesses.Keys) {
                $IsHealthy = Test-ServiceHealth -ServiceName $ServiceName
                $PreviousHealth = $Script:ServiceHealth[$ServiceName]
                
                if (-not $IsHealthy -and $PreviousHealth -eq 'Healthy') {
                    Write-Log -Message "Service became UNHEALTHY" -Level Error -Service $ServiceName
                    $Script:ServiceHealth[$ServiceName] = 'Unhealthy'
                    
                    # Initialize restart counter
                    if (-not $RestartAttempts.ContainsKey($ServiceName)) {
                        $RestartAttempts[$ServiceName] = 0
                    }
                    
                    # Attempt restart (max 3 attempts)
                    if ($RestartAttempts[$ServiceName] -lt 3) {
                        $RestartAttempts[$ServiceName]++
                        Write-Log -Message "Attempting restart ($($RestartAttempts[$ServiceName])/3)..." -Level Warning -Service $ServiceName
                        
                        # Stop crashed service
                        if ($Script:ServiceProcesses[$ServiceName]) {
                            try {
                                $Script:ServiceProcesses[$ServiceName].Kill()
                            }
                            catch {
                                Write-Log -Message "Failed to kill process: $_" -Level Debug -Service $ServiceName
                            }
                        }
                        
                        # Restart based on service type
                        $Service = $Script:Services[$ServiceName]
                        $NewProcess = $null
                        
                        switch ($Service.Type) {
                            'Python' { $NewProcess = Start-PythonService -ServiceName $ServiceName -Service $Service }
                            'Node' { $NewProcess = Start-NodeService -ServiceName $ServiceName -Service $Service }
                        }
                        
                        if ($NewProcess) {
                            Write-Log -Message "Service restarted successfully" -Level Success -Service $ServiceName
                            $RestartAttempts[$ServiceName] = 0  # Reset counter on success
                        }
                        else {
                            Write-Log -Message "Restart failed" -Level Error -Service $ServiceName
                        }
                    }
                    else {
                        Write-Log -Message "Max restart attempts reached. Service marked as FAILED." -Level Error -Service $ServiceName
                        $Script:ServiceHealth[$ServiceName] = 'Failed'
                    }
                }
                elseif ($IsHealthy -and $PreviousHealth -ne 'Healthy') {
                    Write-Log -Message "Service recovered to HEALTHY" -Level Success -Service $ServiceName
                    $Script:ServiceHealth[$ServiceName] = 'Healthy'
                    $RestartAttempts[$ServiceName] = 0
                }
            }
        }
    }
    catch {
        Write-Log -Message "Watchdog interrupted: $_" -Level Warning
    }
}

# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

function Start-Ecosystem {
    Write-Banner "SOMA ECOSYSTEM ORCHESTRATOR"
    
    Write-Log -Message "PowerShell Version: $($PSVersionTable.PSVersion)" -Level Info
    Write-Log -Message "Operating System: $([System.Environment]::OSVersion.VersionString)" -Level Info
    Write-Log -Message "Working Directory: $PSScriptRoot" -Level Info
    Write-Log -Message "Log File: $Script:LogFile" -Level Info
    Write-Log -Message "Log Level: $LogLevel" -Level Info
    
    # Phase 1: Pre-flight checks
    Write-Banner "PHASE 1: PRE-FLIGHT CHECKS"
    
    # Check required tools
    $RequiredTools = @('docker', 'poetry', 'npm', 'python')
    foreach ($Tool in $RequiredTools) {
        $Exists = Get-Command $Tool -ErrorAction SilentlyContinue
        if (-not $Exists) {
            Write-Log -Message "$Tool not found in PATH" -Level Error
            return $false
        }
        else {
            $Version = & $Tool --version 2>&1 | Select-Object -First 1
            Write-Log -Message "$Tool found: $Version" -Level Debug
        }
    }
    
    # Check .env file
    $EnvFile = Join-Path $PSScriptRoot ".env"
    if (-not (Test-Path $EnvFile)) {
        Write-Log -Message ".env file not found. Copy from .env.example" -Level Error
        return $false
    }
    
    Write-Log -Message "Pre-flight checks PASSED" -Level Success
    
    # Phase 2: Docker infrastructure
    Write-Banner "PHASE 2: DOCKER INFRASTRUCTURE"
    
    $DockerSuccess = Start-DockerServices
    if (-not $DockerSuccess) {
        Write-Log -Message "Docker infrastructure failed to start" -Level Error
        return $false
    }
    
    # Phase 3: Database migrations
    Write-Banner "PHASE 3: DATABASE MIGRATIONS"
    
    $MigrationSuccess = Invoke-Migrations
    if (-not $MigrationSuccess) {
        Write-Log -Message "Migrations failed (continuing anyway)" -Level Warning
    }
    
    # Phase 4: Contract validation
    Write-Banner "PHASE 4: API CONTRACT VALIDATION"
    
    $ContractSuccess = Invoke-ContractValidation
    if (-not $ContractSuccess) {
        Write-Log -Message "Contract validation failed (continuing anyway)" -Level Warning
    }
    
    # Phase 5: Start services by priority
    Write-Banner "PHASE 5: STARTING APPLICATION SERVICES"
    
    $ServicesByPriority = $Script:Services.GetEnumerator() | 
    Where-Object { $_.Value.Type -ne 'Docker' } |
    Sort-Object { $_.Value.Priority }
    
    foreach ($Entry in $ServicesByPriority) {
        $ServiceName = $Entry.Key
        $Service = $Entry.Value
        
        Write-Log -Message "Starting $ServiceName (Priority: $($Service.Priority))..." -Level Info -Service $ServiceName
        
        $Process = $null
        switch ($Service.Type) {
            'Python' { $Process = Start-PythonService -ServiceName $ServiceName -Service $Service }
            'Node' { $Process = Start-NodeService -ServiceName $ServiceName -Service $Service }
        }
        
        if (-not $Process) {
            Write-Log -Message "$ServiceName failed to start" -Level Error -Service $ServiceName
            $Script:FailedServices += $ServiceName
            # Continue with other services (decoupled)
        }
        
        # Brief pause between services
        Start-Sleep -Seconds 2
    }
    
    # Phase 6: Summary
    Write-Banner "PHASE 6: STARTUP SUMMARY"
    
    $HealthyCount = ($Script:ServiceHealth.Values | Where-Object { $_ -eq 'Healthy' }).Count
    $TotalCount = $Script:Services.Count
    $Duration = (Get-Date) - $Script:StartTime
    
    Write-Log -Message "Startup completed in $($Duration.TotalSeconds) seconds" -Level Info
    Write-Log -Message "Services: $HealthyCount/$TotalCount healthy" -Level Info
    
    Write-Host "`n╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                       SERVICE STATUS REPORT                           ║" -ForegroundColor Cyan
    Write-Host "╠═══════════════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
    
    foreach ($ServiceName in ($Script:Services.Keys | Sort-Object)) {
        $Status = $Script:ServiceHealth[$ServiceName]
        $Service = $Script:Services[$ServiceName]
        
        $StatusSymbol = switch ($Status) {
            'Healthy' { '✓' }
            'Unhealthy' { '⚠' }
            'Failed' { '✗' }
            default { '?' }
        }
        
        $StatusColor = switch ($Status) {
            'Healthy' { 'Green' }
            'Unhealthy' { 'Yellow' }
            'Failed' { 'Red' }
            default { 'Gray' }
        }
        
        $Line = "║  $StatusSymbol  $($ServiceName.PadRight(20)) Port: $($Service.Port.ToString().PadRight(5)) [$Status]"
        Write-Host $Line.PadRight(72) "║" -ForegroundColor $StatusColor
    }
    
    Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    if ($Script:FailedServices.Count -gt 0) {
        Write-Host "`n⚠ Failed services: $($Script:FailedServices -join ', ')" -ForegroundColor Yellow
        Write-Host "Check logs in: $Script:LogDir" -ForegroundColor Yellow
    }
    
    # Display access URLs
    Write-Host "`n╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "║                          ACCESS URLS                                  ║" -ForegroundColor Magenta
    Write-Host "╠═══════════════════════════════════════════════════════════════════════╣" -ForegroundColor Magenta
    Write-Host "║  Cortex Dashboard:  http://localhost:5173                            ║" -ForegroundColor White
    Write-Host "║  InGress API:       http://localhost:8000/docs                       ║" -ForegroundColor White
    Write-Host "║  InGest API:        http://localhost:8766/docs                       ║" -ForegroundColor White
    Write-Host "║  OmegaKG API:       http://localhost:8765/docs                       ║" -ForegroundColor White
    Write-Host "║  memOS API:         http://localhost:8768/docs                       ║" -ForegroundColor White
    Write-Host "║  Neo4j Browser:     http://localhost:7474                            ║" -ForegroundColor White
    Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
    
    return $HealthyCount -eq $TotalCount
}

# ============================================================================
# CLEANUP & SHUTDOWN
# ============================================================================

function Stop-Ecosystem {
    Write-Banner "SHUTTING DOWN ECOSYSTEM"
    
    Write-Log -Message "Stopping all services gracefully..." -Level Info
    
    # Stop in reverse priority order
    $ServicesByPriority = $Script:ServiceProcesses.GetEnumerator() |
    Sort-Object { $Script:Services[$_.Key].Priority } -Descending
    
    foreach ($Entry in $ServicesByPriority) {
        $ServiceName = $Entry.Key
        $Process = $Entry.Value
        
        try {
            if (-not $Process.HasExited) {
                Write-Log -Message "Stopping service (PID: $($Process.Id))..." -Level Info -Service $ServiceName
                $Process.Kill()
                $Process.WaitForExit(5000)  # Wait up to 5 seconds
                Write-Log -Message "Service stopped" -Level Success -Service $ServiceName
            }
        }
        catch {
            Write-Log -Message "Error stopping service: $_" -Level Warning -Service $ServiceName
        }
    }
    
    Write-Log -Message "Shutdown complete" -Level Success
}

# ============================================================================
# ENTRY POINT
# ============================================================================

try {
    $Success = Start-Ecosystem
    
    if ($Persistent -and $Success) {
        Start-WatchdogLoop
    }
    elseif (-not $Persistent) {
        Write-Host "`nPress any key to stop all services..." -ForegroundColor Cyan
        $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    }
}
catch {
    Write-Log -Message "Fatal error: $_" -Level Error
    Write-Log -Message "Stack trace: $($_.ScriptStackTrace)" -Level Debug
}
finally {
    Stop-Ecosystem
}
