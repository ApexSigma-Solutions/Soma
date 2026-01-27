<#
.SYNOPSIS
    Smart Omega_KG Capture Server Launcher - One command to rule them all.

.DESCRIPTION
    Intelligent server management script that handles:
    - Automatic environment detection (dev/stable)
    - Pre-flight dependency and service checks
    - Multiple launch modes (foreground, background, new terminal)
    - Graceful restart of running instances
    - Port conflict detection and resolution
    - Comprehensive logging

.PARAMETER Mode
    How to run the server:
    - 'foreground' (default): Run in current terminal (Ctrl+C to stop)
    - 'background': Run as a background job (use Stop-OmegaServer to stop)
    - 'terminal': Launch in a new terminal window for observation
    - 'status': Just show current server status
    - 'stop': Stop any running server instance
    - 'restart': Stop existing and start fresh

.PARAMETER Environment
    Target environment: 'dev' (default) or 'stable'
    Auto-detected from current directory if not specified.

.PARAMETER SkipChecks
    Skip pre-flight checks (faster startup, use with caution)

.PARAMETER Force
    Force restart even if server is already running

.PARAMETER Port
    Override the default port (8765 for dev, 8002 for stable)

.PARAMETER Verbose
    Show detailed output during startup

.EXAMPLE
    .\Start-OmegaServer.ps1
    # Start server in foreground with auto-detected environment

.EXAMPLE
    .\Start-OmegaServer.ps1 -Mode background
    # Start server in background, returns immediately

.EXAMPLE
    .\Start-OmegaServer.ps1 -Mode terminal -Environment stable
    # Start stable server in new observable terminal

.EXAMPLE
    .\Start-OmegaServer.ps1 -Mode restart -Force
    # Force restart the server

.NOTES
    Author: Omega_KG Team
    Version: 2.0.0
    Requires: PowerShell 7+, Poetry, Docker
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('foreground', 'background', 'terminal', 'status', 'stop', 'restart')]
    [string]$Mode = 'foreground',

    [Parameter(Position = 1)]
    [ValidateSet('dev', 'stable', 'auto')]
    [string]$Environment = 'auto',

    [switch]$SkipChecks,
    [switch]$Force,
    [int]$Port = 0,
    [switch]$ShowDebug
)

#region Configuration
$ErrorActionPreference = "Stop"
$script:LogFile = Join-Path $env:TEMP "Omega_KG_server.log"
$script:PidFile = Join-Path $env:TEMP "Omega_KG_server.pid"

# Environment configurations
$script:Environments = @{
    dev = @{
        Path = "d:\projects\Omega_KG_dev"
        DefaultPort = 8765
        ContainerPrefix = "apexsigma"
    }
    stable = @{
        Path = "d:\projects\Omega_KG_stable"
        DefaultPort = 8002
        ContainerPrefix = "apexsigma"
    }
}
#endregion

#region Logging Functions
function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('INFO', 'SUCCESS', 'WARN', 'ERROR', 'DEBUG')]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    # Console output with colors
    $color = switch ($Level) {
        'SUCCESS' { 'Green' }
        'WARN'    { 'Yellow' }
        'ERROR'   { 'Red' }
        'DEBUG'   { 'DarkGray' }
        default   { 'Cyan' }
    }

    if ($Level -ne 'DEBUG' -or $ShowDebug) {
        Write-Host $logEntry -ForegroundColor $color
    }

    # File logging
    Add-Content -Path $script:LogFile -Value $logEntry -ErrorAction SilentlyContinue
}

function Write-Banner {
    param([string]$Title)
    $line = "=" * 50
    Write-Host ""
    Write-Host $line -ForegroundColor Magenta
    Write-Host "  $Title" -ForegroundColor White
    Write-Host $line -ForegroundColor Magenta
}
#endregion


function Rotate-Log {
    <#
    .SYNOPSIS
        Rotate log files when they exceed max size (1 MB)
        Keeps up to 5 backup archives
    #>
    param([string]$Path)

    $maxSize = 1MB
    $maxFiles = 5

    if (-Not (Test-Path $Path)) { return }

    $size = (Get-Item $Path).Length
    if ($size -gt $maxSize) {
        Write-Log "Log file exceeded $maxSize, rotating..." -Level INFO

        # Shift older archives (log.1 -> log.2, log.2 -> log.3, etc.)
        for ($i = $maxFiles; $i -ge 1; $i--) {
            $old = "$Path.$i"
            $new = "$Path.$($i+1)"
            if (Test-Path $old) {
                if ($i -eq $maxFiles) {
                    Remove-Item $old -Force -ErrorAction SilentlyContinue
                } else {
                    Rename-Item $old -NewName $new -Force -ErrorAction SilentlyContinue
                }
            }
        }
        # Rename current log to .1
        Rename-Item $Path -NewName "$Path.1" -Force -ErrorAction SilentlyContinue
        Write-Log "Log rotated successfully" -Level SUCCESS
    }
}

#region Environment Detection
function Get-ActiveEnvironment {
    param([string]$RequestedEnv)

    if ($RequestedEnv -ne 'auto') {
        return $RequestedEnv
    }

    # Auto-detect from current directory
    $currentPath = (Get-Location).Path.ToLower()

    if ($currentPath -like "*omega_kg_stable*") {
        return 'stable'
    }
    elseif ($currentPath -like "*omega_kg_dev*") {
        return 'dev'
    }
    elseif ($env:OMEGA_KG_ENV) {
        return $env:OMEGA_KG_ENV
    }
    else {
        # Default to dev
        return 'dev'
    }
}

function Initialize-Environment {
    param([string]$EnvName)

    $config = $script:Environments[$EnvName]
    $projectPath = $config.Path

    if (-not (Test-Path $projectPath)) {
        throw "Project path not found: $projectPath"
    }

    # Change to project directory
    Set-Location $projectPath
    Write-Log "Working directory: $projectPath" -Level DEBUG

    # Load .env file
    $envFile = Join-Path $projectPath ".env"
    if (Test-Path $envFile) {
        Write-Log "Loading environment from .env" -Level DEBUG
        Get-Content $envFile | ForEach-Object {
            $line = $_.Trim()
            if ($line -and $line -notmatch '^\s*#') {
                $parts = $line.Split('=', 2)
                if ($parts.Length -eq 2) {
                    $key = $parts[0].Trim()
                    $value = $parts[1].Trim() -replace '^"|"$' -replace "^'|'$"
                    [Environment]::SetEnvironmentVariable($key, $value, 'Process')
                }
            }
        }
    }

    # Activate virtual environment if not already active
    $venvPath = Join-Path $projectPath ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        if (-not $env:VIRTUAL_ENV -or $env:VIRTUAL_ENV -notlike "*$EnvName*") {
            Write-Log "Activating virtual environment" -Level DEBUG
            & $venvPath
        }
    }

    # Set environment marker
    $env:OMEGA_KG_ENV = $EnvName

    return $config
}
#endregion

#region Process Management
function Get-OmegaServerProcess {
    <#
    .SYNOPSIS
        Find running Omega_KG capture server processes
    #>

    # Check for uvicorn processes
    $uvicornProcs = Get-CimInstance Win32_Process -Filter "Name = 'uvicorn.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "omega_kg[._]capture[._]?server" }

    # Check for python processes running uvicorn
    $pythonProcs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "uvicorn.*omega_kg" -or $_.CommandLine -match "capture.server|capture_server" }

    # Combine and deduplicate
    $allProcs = @()
    if ($uvicornProcs) { $allProcs += $uvicornProcs }
    if ($pythonProcs) { $allProcs += $pythonProcs }

    return $allProcs | Select-Object -Unique
}

function Get-PortProcess {
    param([int]$Port)

    $netstat = netstat -ano | Select-String ":$Port\s"
    if ($netstat) {
        $procId = ($netstat -split '\s+')[-1]
        return Get-Process -Id $procId -ErrorAction SilentlyContinue
    }
    return $null
}

function Stop-OmegaServer {
    <#
    .SYNOPSIS
        Gracefully stop running Omega_KG server
    #>
    param([switch]$Force)

    $processes = Get-OmegaServerProcess

    if (-not $processes) {
        Write-Log "No running Omega_KG server found" -Level WARN
        return $false
    }

    foreach ($proc in $processes) {
        Write-Log "Stopping server process (PID: $($proc.ProcessId))..." -Level INFO

        try {
            $process = Get-Process -Id $proc.ProcessId -ErrorAction Stop

            if (-not $Force) {
                # Try graceful shutdown first
                $process.CloseMainWindow() | Out-Null
                $waited = $process.WaitForExit(5000)

                if (-not $waited) {
                    Write-Log "Graceful shutdown timed out, forcing..." -Level WARN
                    $process.Kill()
                }
            }
            else {
                $process.Kill()
            }

            Write-Log "Process $($proc.ProcessId) stopped" -Level SUCCESS
        }
        catch {
            Write-Log "Failed to stop process $($proc.ProcessId): $_" -Level ERROR
        }
    }

    # Clean up PID file
    if (Test-Path $script:PidFile) {
        Remove-Item $script:PidFile -Force -ErrorAction SilentlyContinue
    }

    # Also check for background jobs
    $jobs = Get-Job -Name "OmegaKG_*" -ErrorAction SilentlyContinue
    if ($jobs) {
        $jobs | Stop-Job -PassThru | Remove-Job
        Write-Log "Cleaned up background jobs" -Level DEBUG
    }

    return $true
}

function Test-PortAvailable {
    param([int]$Port)

    $listener = Get-PortProcess -Port $Port
    return ($null -eq $listener)
}
#endregion

#region Pre-Flight Checks
function Invoke-PreFlightChecks {
    param([hashtable]$Config, [int]$TargetPort)

    Write-Banner "Pre-Flight Checks"
    $allPassed = $true

    # Check 1: Python version
    Write-Log "Checking Python version..." -Level INFO
    try {
        $pythonVersion = (python --version 2>&1) -replace 'Python ', ''
        $major, $minor = $pythonVersion.Split('.')[0..1]
        if ([int]$major -ge 3 -and [int]$minor -ge 12) {
            Write-Log "Python $pythonVersion ✓" -Level SUCCESS
        }
        else {
            Write-Log "Python 3.12+ required, found $pythonVersion" -Level ERROR
            $allPassed = $false
        }
    }
    catch {
        Write-Log "Python not found in PATH" -Level ERROR
        $allPassed = $false
    }

    # Check 2: Poetry
    Write-Log "Checking Poetry..." -Level INFO
    try {
        $poetryVersion = (poetry --version 2>&1) -replace 'Poetry \(version ', '' -replace '\)', ''
        Write-Log "Poetry $poetryVersion ✓" -Level SUCCESS
    }
    catch {
        Write-Log "Poetry not found in PATH" -Level ERROR
        $allPassed = $false
    }

    # Check 3: Virtual environment
    Write-Log "Checking virtual environment..." -Level INFO
    if ($env:VIRTUAL_ENV) {
        Write-Log "venv active: $env:VIRTUAL_ENV ✓" -Level SUCCESS
    }
    else {
        Write-Log "Virtual environment not activated" -Level WARN
    }

    # Check 4: Docker
    Write-Log "Checking Docker..." -Level INFO
    try {
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker is running ✓" -Level SUCCESS
        }
        else {
            Write-Log "Docker is not running" -Level ERROR
            $allPassed = $false
        }
    }
    catch {
        Write-Log "Docker not available" -Level ERROR
        $allPassed = $false
    }

    # Check 5: Neo4j container
    Write-Log "Checking Neo4j container..." -Level INFO
    $neo4jContainer = docker ps -q -f "name=$($Config.ContainerPrefix).neo4j" 2>$null
    if ($neo4jContainer) {
        Write-Log "Neo4j container running ✓" -Level SUCCESS
    }
    else {
        Write-Log "Neo4j container not running (will attempt to start)" -Level WARN
    }

    # Check 6: Port availability
    Write-Log "Checking port $TargetPort availability..." -Level INFO
    if (Test-PortAvailable -Port $TargetPort) {
        Write-Log "Port $TargetPort is available ✓" -Level SUCCESS
    }
    else {
        $portProc = Get-PortProcess -Port $TargetPort
        if ($portProc) {
            Write-Log "Port $TargetPort in use by: $($portProc.ProcessName) (PID: $($portProc.Id))" -Level WARN
        }
        else {
            Write-Log "Port $TargetPort in use by unknown process" -Level WARN
        }
    }

    return $allPassed
}
#endregion

#region Server Start Functions
function Start-ServerForeground {
    param([hashtable]$Config, [int]$Port)

    Write-Banner "Starting Server (Foreground)"
    Write-Log "Server will run at http://127.0.0.1:$Port" -Level INFO
    Write-Log "Press Ctrl+C to stop" -Level INFO
    Write-Host ""

    # Save process ID info
    $processId = [System.Diagnostics.Process]::GetCurrentProcess().Id
    Set-Content -Path $script:PidFile -Value $processId

    try {
        poetry run uvicorn omega_kg.capture_server:app --host 127.0.0.1 --port $Port --log-level info
    }
    finally {
        Remove-Item $script:PidFile -Force -ErrorAction SilentlyContinue
    }
}

function Start-ServerBackground {
    param([hashtable]$Config, [int]$Port)

    Write-Banner "Starting Server (Background)"

    $projectPath = $Config.Path
    $jobName = "OmegaKG_$($env:OMEGA_KG_ENV)_$Port"

    # Remove any existing job with same name
    Get-Job -Name $jobName -ErrorAction SilentlyContinue | Stop-Job -PassThru | Remove-Job

    $job = Start-Job -Name $jobName -ScriptBlock {
        param($path, $port)
        Set-Location $path

        # Activate venv
        $venvActivate = Join-Path $path ".venv\Scripts\Activate.ps1"
        if (Test-Path $venvActivate) {
            & $venvActivate
        }

        # Load .env
        $envFile = Join-Path $path ".env"
        if (Test-Path $envFile) {
            Get-Content $envFile | ForEach-Object {
                $line = $_.Trim()
                if ($line -and $line -notmatch '^\s*#') {
                    $parts = $line.Split('=', 2)
                    if ($parts.Length -eq 2) {
                        $key = $parts[0].Trim()
                        $value = $parts[1].Trim() -replace '^"|"$' -replace "^'|'$"
                        [Environment]::SetEnvironmentVariable($key, $value, 'Process')
                    }
                }
            }
        }

        poetry run uvicorn omega_kg.capture_server:app --host 127.0.0.1 --port $port --log-level info
    } -ArgumentList $projectPath, $Port

    # Wait a moment and check if it started
    Start-Sleep -Seconds 3

    if ($job.State -eq 'Running') {
        # Save job info
        Set-Content -Path $script:PidFile -Value "JOB:$($job.Id)"

        Write-Log "Server started in background (Job ID: $($job.Id))" -Level SUCCESS
        Write-Log "Server running at http://127.0.0.1:$Port" -Level INFO
        Write-Log "" -Level INFO
        Write-Log "Commands:" -Level INFO
        Write-Log "  Get-Job -Id $($job.Id)                    # Check status" -Level INFO
        Write-Log "  Receive-Job -Id $($job.Id)                # View output" -Level INFO
        Write-Log "  .\Start-OmegaServer.ps1 -Mode stop        # Stop server" -Level INFO
    }
    else {
        $errors = Receive-Job -Job $job 2>&1
        Write-Log "Failed to start server: $errors" -Level ERROR
        Remove-Job -Job $job
    }
}

function Start-ServerNewTerminal {
    param([hashtable]$Config, [int]$Port)

    Write-Banner "Starting Server (New Terminal)"

    $projectPath = $Config.Path
    $envName = $env:OMEGA_KG_ENV

    # Build the command to run in new terminal
    $command = @"
Set-Location '$projectPath'
`$Host.UI.RawUI.WindowTitle = 'Omega_KG Server ($envName) - Port $Port'
Write-Host '============================================' -ForegroundColor Cyan
Write-Host '  Omega_KG Capture Server' -ForegroundColor White
Write-Host '  Environment: $envName' -ForegroundColor White
Write-Host '  Port: $Port' -ForegroundColor White
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ''

# Activate venv
`$venvActivate = Join-Path '$projectPath' '.venv\Scripts\Activate.ps1'
if (Test-Path `$venvActivate) { & `$venvActivate }

# Load .env
`$envFile = Join-Path '$projectPath' '.env'
if (Test-Path `$envFile) {
    Get-Content `$envFile | ForEach-Object {
        `$line = `$_.Trim()
        if (`$line -and `$line -notmatch '^\s*#') {
            `$parts = `$line.Split('=', 2)
            if (`$parts.Length -eq 2) {
                `$key = `$parts[0].Trim()
                `$value = `$parts[1].Trim() -replace '^`"|`"`$' -replace "^'|'`$"
                [Environment]::SetEnvironmentVariable(`$key, `$value, 'Process')
            }
        }
    }
}

Write-Host 'Starting server... (Ctrl+C to stop)' -ForegroundColor Yellow
Write-Host ''
poetry run uvicorn omega_kg.capture_server:app --host 127.0.0.1 --port $Port --log-level info
"@

    # Encode command for passing to new PowerShell instance
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($command)
    $encodedCommand = [Convert]::ToBase64String($bytes)

    $process = Start-Process pwsh -ArgumentList "-NoExit", "-EncodedCommand", $encodedCommand -PassThru

    # Save PID
    Set-Content -Path $script:PidFile -Value $process.Id

    Write-Log "Server starting in new terminal window (PID: $($process.Id))" -Level SUCCESS
    Write-Log "Server will be at http://127.0.0.1:$Port" -Level INFO
}
#endregion

#region Status Display
function Show-ServerStatus {
    Write-Banner "Omega_KG Server Status"

    $processes = Get-OmegaServerProcess

    if ($processes) {
        Write-Log "Server is RUNNING" -Level SUCCESS
        foreach ($proc in $processes) {
            Write-Host ""
            Write-Host "  Process ID:    $($proc.ProcessId)" -ForegroundColor White
            Write-Host "  Process Name:  $($proc.Name)" -ForegroundColor White

            # Try to extract port from command line
            if ($proc.CommandLine -match '--port\s+(\d+)') {
                Write-Host "  Port:          $($Matches[1])" -ForegroundColor White
            }

            # Get process start time
            $ps = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
            if ($ps) {
                Write-Host "  Start Time:    $($ps.StartTime)" -ForegroundColor White
                Write-Host "  Memory:        $([math]::Round($ps.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor White
            }
        }
    }
    else {
        Write-Log "Server is NOT RUNNING" -Level WARN
    }

    # Check background jobs
    $jobs = Get-Job -Name "OmegaKG_*" -ErrorAction SilentlyContinue
    if ($jobs) {
        Write-Host ""
        Write-Log "Background Jobs:" -Level INFO
        foreach ($job in $jobs) {
            Write-Host "  Job $($job.Id): $($job.Name) - State: $($job.State)" -ForegroundColor White
        }
    }

    # Show port status
    Write-Host ""
    Write-Log "Port Status:" -Level INFO
    foreach ($env in @('dev', 'stable')) {
        $port = $script:Environments[$env].DefaultPort
        $inUse = -not (Test-PortAvailable -Port $port)
        $status = if ($inUse) { "IN USE" } else { "Available" }
        $color = if ($inUse) { "Yellow" } else { "Green" }
        Write-Host "  $env (port $port): $status" -ForegroundColor $color
    }

    # Docker services
    Write-Host ""
    Write-Log "Docker Services:" -Level INFO
    @("neo4j", "postgres") | ForEach-Object {
        $container = docker ps -f "name=apexsigma.$_" --format "{{.Status}}" 2>$null
        if ($container) {
            Write-Host "  $_`: $container" -ForegroundColor Green
        }
        else {
            Write-Host "  $_`: Not running" -ForegroundColor Yellow
        }
    }
}
#endregion

#region Main Execution
function Main {
    # Rotate log file if too large (> 1MB)
    if ((Test-Path $script:LogFile) -and ((Get-Item $script:LogFile).Length -gt 1MB)) {
        $backupLog = $script:LogFile -replace '\.log$', "_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
        Move-Item $script:LogFile $backupLog -Force
    }

    Write-Log "=== Omega_KG Server Manager Started ===" -Level DEBUG

    # Determine environment
    $activeEnv = Get-ActiveEnvironment -RequestedEnv $Environment
    Write-Log "Environment: $activeEnv" -Level DEBUG

    # Handle status mode early
    if ($Mode -eq 'status') {
        Show-ServerStatus
        return
    }

    # Handle stop mode
    if ($Mode -eq 'stop') {
        Write-Banner "Stopping Server"
        Stop-OmegaServer -Force:$Force
        return
    }

    # Initialize environment and get config
    $config = Initialize-Environment -EnvName $activeEnv

    # Determine port
    $targetPort = if ($Port -gt 0) { $Port } else { $config.DefaultPort }

    # Handle restart mode
    if ($Mode -eq 'restart') {
        Write-Banner "Restarting Server"
        Stop-OmegaServer -Force:$Force
        Start-Sleep -Seconds 2
        $Mode = 'foreground'  # Default to foreground after restart
    }

    # Check for existing processes
    $existingProcs = Get-OmegaServerProcess
    if ($existingProcs -and -not $Force) {
        Write-Log "Server already running (PID: $($existingProcs[0].ProcessId))" -Level WARN
        Write-Log "Use -Force to restart, or -Mode stop to stop" -Level INFO
        return
    }
    elseif ($existingProcs -and $Force) {
        Write-Log "Force flag set, stopping existing server..." -Level INFO
        Stop-OmegaServer -Force
        Start-Sleep -Seconds 2
    }

    # Check port availability
    if (-not (Test-PortAvailable -Port $targetPort)) {
        $portProc = Get-PortProcess -Port $targetPort
        if ($Force) {
            Write-Log "Force stopping process on port $targetPort..." -Level WARN
            Stop-Process -Id $portProc.Id -Force
            Start-Sleep -Seconds 2
        }
        else {
            Write-Log "Port $targetPort is in use by $($portProc.ProcessName)" -Level ERROR
            Write-Log "Use -Force to kill the blocking process" -Level INFO
            return
        }
    }

    # Run pre-flight checks
    if (-not $SkipChecks) {
        $checksPassed = Invoke-PreFlightChecks -Config $config -TargetPort $targetPort
        if (-not $checksPassed) {
            Write-Log "Pre-flight checks failed. Use -SkipChecks to bypass." -Level ERROR
            return
        }
    }
    else {
        Write-Log "Skipping pre-flight checks" -Level WARN
    }

    # Start server based on mode
    switch ($Mode) {
        'foreground' {
            Start-ServerForeground -Config $config -Port $targetPort
        }
        'background' {
            Start-ServerBackground -Config $config -Port $targetPort
        }
        'terminal' {
            Start-ServerNewTerminal -Config $config -Port $targetPort
        }
    }
}

# Run main
try {
    Main
}
catch {
    Write-Log "Fatal error: $_" -Level ERROR
    Write-Log $_.ScriptStackTrace -Level DEBUG
    exit 1
}
#endregion
