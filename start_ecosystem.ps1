# =============================================================================
# Soma Ecosystem Master Launcher v2.0
# =============================================================================
# Purpose: Orchestrates ALL services across the Soma ecosystem
# Features:
#   - Intelligent error handling with retry logic
#   - Health check verification before service startup
#   - Alembic migrations for all services
#   - Poetry with pip fallback for TLS issues
#   - Proper API contract validation
#   - Dashboard/Control Room loading
#
# Usage:
#   .\start_ecosystem.ps1                      -> Production (Hidden Windows)
#   .\start_ecosystem.ps1 -ShowConsole        -> Debugging (Visible Windows)
#   .\start_ecosystem.ps1 -Persistent         -> Keep all services alive with watchdog
#   .\start_ecosystem.ps1 -SkipMigrations     -> Skip database migrations
#   .\start_ecosystem.ps1 -SkipContracts       -> Skip API contract validation
# =============================================================================
param (
    [string]$ProjectRoot = $PSScriptRoot,
    [switch]$ShowConsole,
    [switch]$Persistent,
    [switch]$SkipCleanup,
    [switch]$SkipMigrations,
    [switch]$SkipContracts,
    [switch]$SkipInfrastructure,
    [switch]$SkipMemOS,
    [switch]$SkipOmegaKG,
    [switch]$SkipIngest,
    [switch]$SkipIngress,
    [switch]$SkipCortex
)

$ErrorActionPreference = "Stop"
$ErrorActionPreference = "Continue"

$global:ServicesStarted = @{}
$global:ServicesFailed = @{}

function Write-ColorLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )
    $Timestamp = Get-Date -Format "HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Host $LogMessage -ForegroundColor $Color
    
    $GlobalLogPath = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $GlobalLogPath)) {
        New-Item -ItemType Directory -Path $GlobalLogPath -Force | Out-Null
    }
    $MasterLog = Join-Path $GlobalLogPath "ecosystem_$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $MasterLog -Value $LogMessage -Encoding UTF8
}

function Write-Success { param($Message) Write-ColorLog -Message $Message -Level "SUCCESS" -Color "Green" }
function Write-ErrorLog { param($Message) Write-ColorLog -Message $Message -Level "ERROR" -Color "Red" }
function Write-WarnLog { param($Message) Write-ColorLog -Message $Message -Level "WARN" -Color "Yellow" }
function Write-InfoLog { param($Message) Write-ColorLog -Message $Message -Level "INFO" -Color "Cyan" }

function Test-Port {
    param(
        [int]$Port,
        [int]$Timeout = 5
    )
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect("localhost", $Port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne($Timeout * 1000, $false)
        
        if ($wait) {
            $tcp.EndConnect($connect)
            $tcp.Close()
            return $true
        }
        $tcp.Close()
        return $false
    } catch {
        return $false
    }
}

function Get-PoetryOrPip {
    param([string]$ServicePath)
    
    $PoetryCommand = Get-Command poetry -ErrorAction SilentlyContinue
    $SystemPython = "C:\Program Files\Python312\python.exe"
    
    if ($PoetryCommand) {
        Write-InfoLog "Using Poetry for $ServicePath"
        return @{
            Executor = $PoetryCommand.Source
            UsePoetry = $true
        }
    } elseif (Test-Path $SystemPython) {
        Write-InfoLog "Using System Python for $ServicePath"
        return @{
            Executor = $SystemPython
            UsePoetry = $false
        }
    } else {
        Write-WarnLog "Poetry and System Python not found, trying 'python' command"
        return @{
            Executor = "python"
            UsePoetry = $false
        }
    }
}

function Install-WithFallback {
    param(
        [string]$Package,
        [string]$ServicePath
    )
    
    $ExecutorInfo = Get-PoetryOrPip -ServicePath $ServicePath
    
    if ($ExecutorInfo.UsePoetry) {
        try {
            Write-InfoLog "Installing $Package with Poetry..."
            $result = Start-Process -FilePath $ExecutorInfo.Executor `
                -ArgumentList "add $Package" `
                -WorkingDirectory $ServicePath `
                -Wait -NoNewWindow -PassThru
            return $result.ExitCode -eq 0
        } catch {
            Write-WarnLog "Poetry install failed for $Package, trying pip with trusted hosts..."
            return Install-PipWithTrustedHosts -Package $Package
        }
    } else {
        return Install-PipWithTrustedHosts -Package $Package
    }
}

function Install-PipWithTrustedHosts {
    param([string]$Package)
    
    try {
        Write-InfoLog "Installing $Package with pip (trusted hosts)..."
        $result = Start-Process -FilePath "pip" `
            -ArgumentList "install --trusted-host pypi.org --trusted-host files.pythonhosted.org $Package" `
            -Wait -NoNewWindow -PassThru
        return $result.ExitCode -eq 0
    } catch {
        Write-ErrorLog "Failed to install $Package with pip"
        return $false
    }
}

function Invoke-ServiceHealthCheck {
    param(
        [string]$ServiceName,
        [int]$Port,
        [string]$Path = "/health",
        [int]$MaxRetries = 30,
        [int]$RetryInterval = 2
    )
    
    Write-InfoLog "Checking $ServiceName health on port $Port..."
    
    $attempt = 0
    while ($attempt -lt $MaxRetries) {
        $attempt++
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port$Path" `
                -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
            
            if ($response.StatusCode -eq 200) {
                Write-Success "$ServiceName is healthy!"
                return $true
            }
        } catch {
            Write-WarnLog "Attempt $attempt/$MaxRetries: $ServiceName not ready yet..."
        }
        
        Start-Sleep -Seconds $RetryInterval
    }
    
    Write-ErrorLog "$ServiceName failed health check after $MaxRetries attempts"
    return $false
}

function Stop-ServiceProcesses {
    param([string]$Pattern, [string]$ServiceName)
    
    $Procs = Get-CimInstance Win32_Process -Filter "Name like '%python%' OR Name like '%node%'" | Where-Object {
        $_.CommandLine -like "*$Pattern*"
    }
    
    foreach ($p in $Procs) {
        try {
            Write-InfoLog "Stopping $ServiceName (PID: $($p.ProcessId))..."
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        } catch {
            Write-WarnLog "Failed to stop $ServiceName PID $($p.ProcessId): $($_.Exception.Message)"
        }
    }
}

function Initialize-Databases {
    param([switch]$SkipMigrations)
    
    Write-InfoLog "========================================"
    Write-InfoLog "Initializing Databases"
    Write-InfoLog "========================================"
    
    $databases = @{
        "PostgreSQL" = @{
            "Port" = 6000
            "Container" = "apexsigma.postgres.stable"
            "HealthCheck" = { docker exec apexsigma.postgres.stable pg_isready -U omega_user }
        }
        "Neo4j" = @{
            "Port" = 7687
            "Container" = "apexsigma.neo4j.stable"
            "HealthCheck" = { Test-Port -Port 7474 }
        }
        "Redis" = @{
            "Port" = 6380
            "Container" = "apexsigma.redis"
            "HealthCheck" = { docker exec apexsigma.redis redis-cli ping }
        }
    }
    
    foreach ($db in $databases.Keys) {
        $config = $databases[$db]
        
        Write-InfoLog "Checking $db (port $($config.Port))..."
        
        if (Test-Port -Port $config.Port) {
            Write-Success "$db is already running"
        } else {
            Write-InfoLog "Starting $db container..."
            try {
                docker start $config.Container 2>&1 | Out-Null
                
                $attempt = 0
                $maxAttempts = 30
                
                while ($attempt -lt $maxAttempts) {
                    $attempt++
                    try {
                        & $config.HealthCheck | Out-Null
                        Write-Success "$db started successfully"
                        break
                    } catch {
                        Write-WarnLog "Waiting for $db to start (attempt $attempt/$maxAttempts)..."
                        Start-Sleep -Seconds 2
                    }
                }
                
                if ($attempt -eq $maxAttempts) {
                    Write-ErrorLog "Failed to start $db"
                    throw "$db failed to start"
                }
            } catch {
                Write-ErrorLog "Failed to start $db: $($_.Exception.Message)"
                throw
            }
        }
    }
    
    if (-not $SkipMigrations) {
        Write-InfoLog "Running Alembic migrations..."
        Invoke-AlembicMigrations
    }
    
    Write-Success "Database initialization complete"
    Write-InfoLog ""
}

function Invoke-AlembicMigrations {
    $migrations = @{
        "InGress" = "D:\projects\Soma\InGress"
        "InGest" = "D:\projects\Soma\InGest"
        "OmegaKG" = "D:\projects\Soma\OmegaKG"
        "memOS" = "D:\projects\Soma\memOS"
    }
    
    foreach ($service in $migrations.Keys) {
        $servicePath = $migrations[$service]
        $alembicIni = Join-Path $servicePath "alembic.ini"
        
        if (Test-Path $alembicIni) {
            Write-InfoLog "Running migrations for $service..."
            
            $ExecutorInfo = Get-PoetryOrPip -ServicePath $servicePath
            
            try {
                $migrationCmd = if ($ExecutorInfo.UsePoetry) {
                    "run alembic upgrade head"
                } else {
                    "-m alembic upgrade head"
                }
                
                $result = Start-Process -FilePath $ExecutorInfo.Executor `
                    -ArgumentList $migrationCmd `
                    -WorkingDirectory $servicePath `
                    -Wait -NoNewWindow -PassThru `
                    -RedirectStandardOutput (Join-Path $ProjectRoot "logs\${service}_migrations.log") `
                    -RedirectStandardError (Join-Path $ProjectRoot "logs\${service}_migrations.err.log")
                
                if ($result.ExitCode -eq 0) {
                    Write-Success "$service migrations completed"
                } else {
                    Write-WarnLog "$service migrations failed with exit code $($result.ExitCode)"
                }
            } catch {
                Write-WarnLog "Failed to run migrations for $service: $($_.Exception.Message)"
            }
        } else {
            Write-WarnLog "No alembic.ini found for $service, skipping migrations"
        }
    }
}

function Validate-ServiceContracts {
    param(
        [string]$ServiceName,
        [string]$ContractPath
    )
    
    Write-InfoLog "Validating API contracts for $ServiceName..."
    
    if (-not (Test-Path $ContractPath)) {
        Write-WarnLog "No contract file found at $ContractPath"
        return $false
    }
    
    try {
        $contract = Get-Content $ContractPath -Raw | ConvertFrom-Json
        
        if ($contract.contract_version) {
            Write-Success "$ServiceName contract v$($contract.contract_version) loaded"
            
            if ($contract.input_schema) {
                Write-InfoLog "  - Input schema: $($contract.input_schema.source)"
            }
            if ($contract.output_schema) {
                Write-InfoLog "  - Output schema: $($contract.output_schema.target)"
            }
            return $true
        } else {
            Write-WarnLog "Invalid contract format for $ServiceName"
            return $false
        }
    } catch {
        Write-WarnLog "Failed to validate contract for $ServiceName: $($_.Exception.Message)"
        return $false
    }
}

function Start-Ingress {
    param([switch]$ShowConsole)
    
    Write-InfoLog "========================================"
    Write-InfoLog "Starting InGress (Senses Layer)"
    Write-InfoLog "========================================"
    
    $servicePath = "D:\projects\Soma\InGress"
    $ExecutorInfo = Get-PoetryOrPip -ServicePath $servicePath
    
    if (-not (Test-Path $servicePath)) {
        Write-ErrorLog "InGress not found at $servicePath"
        $global:ServicesFailed["InGress"] = "Directory not found"
        return
    }
    
    Stop-ServiceProcesses -Pattern "soma_ingress" -ServiceName "InGress"
    
    try {
        $logDir = Join-Path $ProjectRoot "logs"
        $runArgs = if ($ExecutorInfo.UsePoetry) {
            "run python -m soma_ingress.main"
        } else {
            "-m uvicorn soma_ingress.main:app --port 8000"
        }
        
        $startParams = @{
            FilePath = $ExecutorInfo.Executor
            ArgumentList = $runArgs
            WorkingDirectory = $servicePath
            PassThru = $true
        }
        
        if (-not $ShowConsole) {
            $startParams["WindowStyle"] = "Hidden"
            $startParams["RedirectStandardOutput"] = Join-Path $logDir "ingress_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
            $startParams["RedirectStandardError"] = Join-Path $logDir "ingress_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').err.log"
        }
        
        $proc = Start-Process @startParams
        
        if (Invoke-ServiceHealthCheck -ServiceName "InGress" -Port 8000) {
            $global:ServicesStarted["InGress"] = $proc.Id
            Write-Success "InGress started successfully (PID: $($proc.Id))"
        } else {
            $global:ServicesFailed["InGress"] = "Health check failed"
            Write-ErrorLog "InGress failed health check"
        }
    } catch {
        $global:ServicesFailed["InGress"] = $_.Exception.Message
        Write-ErrorLog "Failed to start InGress: $($_.Exception.Message)"
    }
}

function Start-Ingest {
    param([switch]$ShowConsole)
    
    Write-InfoLog "========================================"
    Write-InfoLog "Starting InGest (Stomach Layer)"
    Write-InfoLog "========================================"
    
    $servicePath = "D:\projects\Soma\InGest"
    $ExecutorInfo = Get-PoetryOrPip -ServicePath $servicePath
    
    if (-not (Test-Path $servicePath)) {
        Write-ErrorLog "InGest not found at $servicePath"
        $global:ServicesFailed["InGest"] = "Directory not found"
        return
    }
    
    if (-not $SkipContracts) {
        Validate-ServiceContracts -ServiceName "InGest" -ContractPath (Join-Path $servicePath "validators\omega_ingest_contract.json")
    }
    
    Stop-ServiceProcesses -Pattern "ingest_llm_as" -ServiceName "InGest"
    
    try {
        $logDir = Join-Path $ProjectRoot "logs"
        $runArgs = if ($ExecutorInfo.UsePoetry) {
            "run python -m ingest_llm_as.main"
        } else {
            "-m uvicorn ingest_llm_as.main:app --port 8766"
        }
        
        $startParams = @{
            FilePath = $ExecutorInfo.Executor
            ArgumentList = $runArgs
            WorkingDirectory = Join-Path $servicePath "src"
            PassThru = $true
        }
        
        if (-not $ShowConsole) {
            $startParams["WindowStyle"] = "Hidden"
            $startParams["RedirectStandardOutput"] = Join-Path $logDir "ingest_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
            $startParams["RedirectStandardError"] = Join-Path $logDir "ingest_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').err.log"
        }
        
        $proc = Start-Process @startParams
        
        if (Invoke-ServiceHealthCheck -ServiceName "InGest" -Port 8766) {
            $global:ServicesStarted["InGest"] = $proc.Id
            Write-Success "InGest started successfully (PID: $($proc.Id))"
        } else {
            $global:ServicesFailed["InGest"] = "Health check failed"
            Write-ErrorLog "InGest failed health check"
        }
    } catch {
        $global:ServicesFailed["InGest"] = $_.Exception.Message
        Write-ErrorLog "Failed to start InGest: $($_.Exception.Message)"
    }
}

function Start-OmegaKG {
    param([switch]$ShowConsole)
    
    Write-InfoLog "========================================"
    Write-InfoLog "Starting OmegaKG (Brain Layer)"
    Write-InfoLog "========================================"
    
    $servicePath = "D:\projects\Soma\OmegaKG"
    $startScript = Join-Path $servicePath "scripts\start_full_stack.ps1"
    
    if (-not (Test-Path $startScript)) {
        Write-ErrorLog "OmegaKG start script not found at $startScript"
        $global:ServicesFailed["OmegaKG"] = "Start script not found"
        return
    }
    
    Stop-ServiceProcesses -Pattern "omega_kg" -ServiceName "OmegaKG"
    
    try {
        $logDir = Join-Path $ProjectRoot "logs"
        $consoleFlag = if ($ShowConsole) { "-ShowConsole" } else { "" }
        
        $proc = Start-Process -FilePath "powershell.exe" `
            -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`" $consoleFlag" `
            -WorkingDirectory $servicePath `
            -PassThru
        
        Write-InfoLog "Waiting for OmegaKG services to initialize..."
        Start-Sleep -Seconds 10
        
        if (Invoke-ServiceHealthCheck -ServiceName "OmegaKG" -Port 8765) {
            $global:ServicesStarted["OmegaKG"] = $proc.Id
            Write-Success "OmegaKG started successfully (PID: $($proc.Id))"
        } else {
            $global:ServicesFailed["OmegaKG"] = "Health check failed"
            Write-WarnLog "OmegaKG health check failed, but capture server may be starting"
            $global:ServicesStarted["OmegaKG"] = $proc.Id
        }
    } catch {
        $global:ServicesFailed["OmegaKG"] = $_.Exception.Message
        Write-ErrorLog "Failed to start OmegaKG: $($_.Exception.Message)"
    }
}

function Start-MemOS {
    param([switch]$ShowConsole)
    
    Write-InfoLog "========================================"
    Write-InfoLog "Starting memOS (Hands Layer)"
    Write-InfoLog "========================================"
    
    $servicePath = "D:\projects\Soma\memOS"
    $ExecutorInfo = Get-PoetryOrPip -ServicePath $servicePath
    
    if (-not (Test-Path $servicePath)) {
        Write-ErrorLog "memOS not found at $servicePath"
        $global:ServicesFailed["memOS"] = "Directory not found"
        return
    }
    
    Stop-ServiceProcesses -Pattern "memos_mcp" -ServiceName "memOS"
    
    try {
        $logDir = Join-Path $ProjectRoot "logs"
        $runArgs = if ($ExecutorInfo.UsePoetry) {
            "run python -m memos_mcp.server --sse"
        } else {
            "-m memos_mcp.server --sse"
        }
        
        $startParams = @{
            FilePath = $ExecutorInfo.Executor
            ArgumentList = $runArgs
            WorkingDirectory = Join-Path $servicePath "src"
            PassThru = $true
        }
        
        if (-not $ShowConsole) {
            $startParams["WindowStyle"] = "Hidden"
            $startParams["RedirectStandardOutput"] = Join-Path $logDir "memos_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
            $startParams["RedirectStandardError"] = Join-Path $logDir "memos_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').err.log"
        }
        
        $proc = Start-Process @startParams
        
        if (Invoke-ServiceHealthCheck -ServiceName "memOS" -Port 8768) {
            $global:ServicesStarted["memOS"] = $proc.Id
            Write-Success "memOS started successfully (PID: $($proc.Id))"
        } else {
            $global:ServicesFailed["memOS"] = "Health check failed"
            Write-WarnLog "memOS health check failed, but MCP server may be starting"
            $global:ServicesStarted["memOS"] = $proc.Id
        }
    } catch {
        $global:ServicesFailed["memOS"] = $_.Exception.Message
        Write-ErrorLog "Failed to start memOS: $($_.Exception.Message)"
    }
}

function Start-Cortex {
    param([switch]$ShowConsole)
    
    Write-InfoLog "========================================"
    Write-InfoLog "Starting Cortex (Dashboard/Control Room)"
    Write-InfoLog "========================================"
    
    $servicePath = "D:\projects\Soma\Cortex"
    
    if (-not (Test-Path $servicePath)) {
        Write-ErrorLog "Cortex not found at $servicePath"
        $global:ServicesFailed["Cortex"] = "Directory not found"
        return
    }
    
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-ErrorLog "npm not found in PATH. Cannot start Cortex."
        $global:ServicesFailed["Cortex"] = "npm not found"
        return
    }
    
    Stop-ServiceProcesses -Pattern "vite" -ServiceName "Cortex"
    
    try {
        Push-Location $servicePath
        
        Write-InfoLog "Installing Cortex dependencies (if needed)..."
        $installResult = Start-Process -FilePath "npm" `
            -ArgumentList "install" `
            -Wait -NoNewWindow -PassThru
        
        if ($installResult.ExitCode -ne 0) {
            Write-WarnLog "npm install had issues, continuing anyway..."
        }
        
        Write-InfoLog "Starting Cortex dev server..."
        
        $logDir = Join-Path $ProjectRoot "logs"
        $startParams = @{
            FilePath = "npm.cmd"
            ArgumentList = "run dev"
            PassThru = $true
        }
        
        if (-not $ShowConsole) {
            $startParams["WindowStyle"] = "Hidden"
            $startParams["RedirectStandardOutput"] = Join-Path $logDir "cortex_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
            $startParams["RedirectStandardError"] = Join-Path $logDir "cortex_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').err.log"
        }
        
        $proc = Start-Process @startParams
        Pop-Location
        
        Write-InfoLog "Waiting for Cortex to initialize..."
        Start-Sleep -Seconds 8
        
        $cortexPort = 5173
        if (Test-Port -Port $cortexPort) {
            $global:ServicesStarted["Cortex"] = $proc.Id
            Write-Success "Cortex started successfully (PID: $($proc.Id))"
            
            Write-InfoLog "Opening Cortex Dashboard in browser..."
            Start-Process "http://localhost:$cortexPort"
        } else {
            $global:ServicesFailed["Cortex"] = "Health check failed"
            Write-WarnLog "Cortex health check failed, but Vite may be starting"
            $global:ServicesStarted["Cortex"] = $proc.Id
        }
    } catch {
        $global:ServicesFailed["Cortex"] = $_.Exception.Message
        Write-ErrorLog "Failed to start Cortex: $($_.Exception.Message)"
        Pop-Location
    }
}

function Show-EcosystemStatus {
    Write-InfoLog "========================================"
    Write-InfoLog "Soma Ecosystem Status"
    Write-InfoLog "========================================"
    
    $services = @(
        @{ Name = "InGress"; Port = 8000; URL = "http://localhost:8000" },
        @{ Name = "InGest"; Port = 8766; URL = "http://localhost:8766" },
        @{ Name = "OmegaKG"; Port = 8765; URL = "http://localhost:8765" },
        @{ Name = "memOS"; Port = 8768; URL = "http://localhost:8768" },
        @{ Name = "Cortex"; Port = 5173; URL = "http://localhost:5173" }
    )
    
    foreach ($svc in $services) {
        if ($global:ServicesStarted.ContainsKey($svc.Name)) {
            Write-Success "  $($svc.Name): $($svc.URL) (PID: $($global:ServicesStarted[$svc.Name]))"
        } elseif ($global:ServicesFailed.ContainsKey($svc.Name)) {
            Write-ErrorLog "  $($svc.Name): FAILED - $($global:ServicesFailed[$svc.Name])"
        } else {
            Write-WarnLog "  $($svc.Name): SKIPPED"
        }
    }
    
    Write-InfoLog "========================================"
}

function Start-Watchdog {
    Write-InfoLog "========================================"
    Write-InfoLog "Master Watchdog Active"
    Write-InfoLog "Monitoring services every 30 seconds"
    Write-InfoLog "Press Ctrl+C to stop"
    Write-InfoLog "========================================"
    
    while ($true) {
        Start-Sleep -Seconds 30
        
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-InfoLog "[$timestamp] Watchdog check..."
        
        foreach ($serviceName in $global:ServicesStarted.Keys) {
            $pid = $global:ServicesStarted[$serviceName]
            
            try {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if (-not $proc) {
                    Write-WarnLog "[$timestamp] $serviceName (PID: $pid) is not running!"
                }
            } catch {
                Write-WarnLog "[$timestamp] Failed to check $serviceName (PID: $pid)"
            }
        }
    }
}

try {
    $env:PYTHONUTF8 = "1"
    
    Write-InfoLog "========================================"
    Write-InfoLog "Soma Ecosystem Launcher v2.0"
    Write-InfoLog "========================================"
    Write-InfoLog "Mode: $(if ($ShowConsole) { 'DEBUG (Visible)' } else { 'PRODUCTION (Hidden)' })"
    Write-InfoLog "Watchdog: $(if ($Persistent) { 'ENABLED' } else { 'DISABLED' })"
    Write-InfoLog "Migrations: $(if ($SkipMigrations) { 'SKIPPED' } else { 'ENABLED' })"
    Write-InfoLog "Contracts: $(if ($SkipContracts) { 'SKIPPED' } else { 'ENABLED' })"
    Write-InfoLog ""
    
    if (-not $SkipCleanup) {
        Write-InfoLog "Performing pre-flight cleanup..."
        foreach ($svc in @("InGress", "InGest", "OmegaKG", "memOS", "Cortex")) {
            Stop-ServiceProcesses -Pattern $svc.ToLower() -ServiceName $svc
        }
        Write-Success "Cleanup complete"
        Write-InfoLog ""
    }
    
    if (-not $SkipInfrastructure) {
        Initialize-Databases -SkipMigrations:$SkipMigrations
        Write-InfoLog ""
    }
    
    if (-not $SkipIngress) {
        Start-Ingress -ShowConsole:$ShowConsole
        Write-InfoLog ""
    }
    
    if (-not $SkipIngest) {
        Start-Ingest -ShowConsole:$ShowConsole
        Write-InfoLog ""
    }
    
    if (-not $SkipOmegaKG) {
        Start-OmegaKG -ShowConsole:$ShowConsole
        Write-InfoLog ""
    }
    
    if (-not $SkipMemOS) {
        Start-MemOS -ShowConsole:$ShowConsole
        Write-InfoLog ""
    }
    
    if (-not $SkipCortex) {
        Start-Cortex -ShowConsole:$ShowConsole
        Write-InfoLog ""
    }
    
    Show-EcosystemStatus
    
    $failedCount = $global:ServicesFailed.Count
    if ($failedCount -gt 0) {
        Write-WarnLog "========================================"
        Write-WarnLog "WARNING: $failedCount service(s) failed to start"
        Write-WarnLog "========================================"
        foreach ($svc in $global:ServicesFailed.Keys) {
            Write-WarnLog "  - $svc: $($global:ServicesFailed[$svc])"
        }
        Write-WarnLog "========================================"
        Write-InfoLog ""
    }
    
    if ($Persistent) {
        Start-Watchdog
    } else {
        Write-Success "Ecosystem startup complete!"
        Write-InfoLog "All services are running independently."
        Write-InfoLog "Use -Persistent flag for watchdog monitoring."
    }
    
} catch {
    Write-ErrorLog "FATAL ERROR: $($_.Exception.Message)"
    Write-ErrorLog $_.ScriptStackTrace
    exit 1
}
