# =============================================================================
# OmegaKG Ecosystem Master Launcher
# =============================================================================
# Purpose: Orchestrates ALL services across the OmegaKG ecosystem
# Usage:
#   .\start_ecosystem.ps1                     -> Production (Hidden Windows)
#   .\start_ecosystem.ps1 -ShowConsole       -> Debugging (Visible Windows)
#   .\start_ecosystem.ps1 -Persistent        -> Keep all services alive with watchdog
#   .\start_ecosystem.ps1 -ShowConsole -Persistent -> Debug + Watchdog
#
# Services Started:
#   - memOS.MCP Server (Port 8768)
#   - Redis (Port 6379)
#   - OmegaKG Capture Server (Port 8765)
#   - OmegaKG Embedding Worker
#   - OmegaKG Vector Index Worker
#   - InGest-LLM.as API Server (Port 8766)
#   - InGest-LLM.as Cloudflared Tunnel
#   - CortexBridge Frontend (Port 5173/5174)
# =============================================================================

param (
    [string]$ProjectRoot = $PSScriptRoot,
    [switch]$ShowConsole,
    [switch]$Persistent,
    [switch]$SkipCleanup,
    [switch]$SkipMemOS,
    [switch]$SkipOmegaKG,
    [switch]$SkipIngestLLM,
    [switch]$SkipCortexBridge
)

$ErrorActionPreference = "Stop"

# --- 0. ENVIRONMENT SETUP ---
$env:PYTHONUTF8 = "1"


# --- 1. SETUP LOGGING ---
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Time = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$MasterLog = Join-Path $LogDir "ecosystem_$Time.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Output $LogMessage
    Add-Content -Path $MasterLog -Value $LogMessage
}

$WindowStyle = if ($ShowConsole) { "Normal" } else { "Hidden" }

Write-Log "========================================" "INFO"
Write-Log "OmegaKG Ecosystem Startup" "INFO"
Write-Log "========================================" "INFO"
Write-Log "Mode: $(if ($ShowConsole) { 'DEBUG (Visible Windows)' } else { 'PRODUCTION (Hidden)' })"
Write-Log "Watchdog: $(if ($Persistent) { 'ENABLED' } else { 'DISABLED' })"
Write-Log "Master Log: $MasterLog"
Write-Log ""

# --- 1B. HELPER FUNCTIONS ---
function Clean-Networking {
    Write-Log "Resetting Windows NAT Driver (fixes port exclusions)..." "WARN"
    try {
        # Check for Admin privileges by attempting a privileged command
        $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        
        if ($isAdmin) {
            Start-Process net -ArgumentList "stop winnat" -Wait -NoNewWindow -ErrorAction SilentlyContinue
            Start-Process net -ArgumentList "start winnat" -Wait -NoNewWindow -ErrorAction SilentlyContinue
            Write-Log "Windows NAT Driver reset complete." "INFO"
        } else {
             Write-Log "Skipping WINNAT reset (Requires Administrator privileges)." "WARN"
        }
    } catch {
        Write-Log "Failed to reset WINNAT: $($_.Exception.Message)" "ERROR"
    }
}

function Kill-TargetProcess {
    param([string]$Pattern, [string]$Name="Process")
    
    $Procs = Get-CimInstance Win32_Process -Filter "Name like '%python%' OR Name like '%node%' OR Name like '%cloudflared%'" | Where-Object { 
        $_.CommandLine -like "*$Pattern*" 
    }
    
    foreach ($p in $Procs) {
        try {
            Write-Log "  [Cleanup] Killing $Name (PID: $($p.ProcessId))..." "WARN"
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Log "  [Cleanup] Failed to kill PID $($p.ProcessId): $($_.Exception.Message)" "WARN"
        }
    }
}

function Cleanup-Everything {
    Write-Log "Performing Pre-flight Cleanup..." "INFO"
    
    # 0. Networking (Port Exclusions)
    Clean-Networking

    # 1. memOS.MCP
    Kill-TargetProcess "memos_mcp" "memOS.MCP"
    
    # 2. OmegaKG Capture
    Kill-TargetProcess "omega_kg.capture_server" "OmegaKG Capture"
    
    # 3. Workers
    Kill-TargetProcess "omega_kg.workers" "OmegaKG Worker"
    
    # 4. InGest-LLM
    Kill-TargetProcess "ingest_llm_as" "InGest-LLM"
    
    # 5. CortexBridge (Node/Vite)
    # Note: Node often spawns children, we try to catch the main vite process
    Kill-TargetProcess "vite" "CortexBridge (Vite)"
    
    # 6. Cloudflared
    Kill-TargetProcess "valhalla-gateway" "Cloudflared"
    
    Write-Log "Cleanup complete." "INFO"
    Write-Log ""
}

# --- 1C. EXECUTE CLEANUP ---
if (-not $SkipCleanup) {
    Cleanup-Everything
} else {
    Write-Log "Skipping Cleanup (-SkipCleanup active)" "INFO"
}

# --- 2. CHECK PREREQUISITES ---
Write-Log "Checking prerequisites..." "INFO"

# Check Redis
try {
    $redisTest = Test-NetConnection -ComputerName localhost -Port 6380 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($redisTest.TcpTestSucceeded) {
        Write-Log "  ✅ Redis running on port 6380" "INFO"
    } else {
        Write-Log "  ❌ Redis not running - Starting..." "WARN"
        docker start apexsigma.redis 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Log "  Starting new Redis container..." "INFO"
            docker run -d -p 6380:6379 --name apexsigma.redis redis:7-alpine | Out-Null
        }
        Start-Sleep -Seconds 2
        Write-Log "  ✅ Redis started" "INFO"
    }
} catch {
    Write-Log "  ⚠️  Could not verify Redis status" "WARN"
}

# Check PostgreSQL
try {
    $pgTest = Test-NetConnection -ComputerName localhost -Port 6000 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($pgTest.TcpTestSucceeded) {
        Write-Log "  ✅ PostgreSQL running on port 6000" "INFO"
    } else {
        Write-Log "  ❌ PostgreSQL not running!" "ERROR"
        Write-Log "  Start with: docker start apexsigma.postgres.stable" "INFO"
    }
} catch {
    Write-Log "  ⚠️  Could not verify PostgreSQL status" "WARN"
}

# Check Ollama
try {
    $ollamaTest = Test-NetConnection -ComputerName localhost -Port 11434 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($ollamaTest.TcpTestSucceeded) {
        Write-Log "  ✅ Ollama running on port 11434" "INFO"
    } else {
        Write-Log "  ❌ Ollama not running!" "ERROR"
    }
} catch {
    Write-Log "  ⚠️  Could not verify Ollama status" "WARN"
}

Write-Log ""

# --- 3. START MEMOS.MCP SERVER ---
$MemosProc = $null
if (-not $SkipMemOS) {
    Write-Log "========================================" "INFO"
    Write-Log "Starting memOS.MCP Server" "INFO"
    Write-Log "========================================" "INFO"
    
    $MemosPath = Join-Path $ProjectRoot "memos.MCP"
    $MemosServerScript = Join-Path $MemosPath "src\memos_mcp\server.py"
    
    if (Test-Path $MemosServerScript) {
        # Check if already running
        $ExistingMemos = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -like "*memos_mcp*server*"
        } | Select-Object -First 1
        
        if ($ExistingMemos) {
            Write-Log "  [i] memOS.MCP already running (PID: $($ExistingMemos.Id))" "INFO"
            $MemosProc = $ExistingMemos
        } else {
            try {
                Push-Location $MemosPath
                $MemosLog = Join-Path $LogDir "memos_mcp_$Time.log"
                $MemosErrLog = Join-Path $LogDir "memos_mcp_$Time.err.log"
                
                $PoetryCommand = Get-Command poetry -ErrorAction SilentlyContinue
                $SystemPython = "C:\Program Files\Python312\python.exe"

                if ($PoetryCommand) {
                    $MemosExecutor = $PoetryCommand.Source
                    $MemosArgsList = "run python src/memos_mcp/server.py --sse"
                } elseif (Test-Path $SystemPython) {
                    $MemosExecutor = $SystemPython
                    $MemosArgsList = "-m poetry run python src/memos_mcp/server.py --sse"
                } else {
                    $MemosExecutor = "python"
                    $MemosArgsList = "-m poetry run python src/memos_mcp/server.py --sse"
                }
                
                # Store for Watchdog Restart
                $script:MemosExecutor = $MemosExecutor
                $script:MemosArgsList = $MemosArgsList

                $MemosArgs = @{
                    FilePath = $MemosExecutor
                    ArgumentList = $MemosArgsList
                    WindowStyle = $WindowStyle
                    PassThru = $true
                    WorkingDirectory = $MemosPath
                }
                
                if (-not $ShowConsole) {
                    $MemosArgs['RedirectStandardOutput'] = $MemosLog
                    $MemosArgs['RedirectStandardError'] = $MemosErrLog
                }
                
                $MemosProc = Start-Process @MemosArgs
                Pop-Location
                
                Write-Log "  [+] memOS.MCP started (PID: $($MemosProc.Id))" "INFO"
                Write-Log "  [+] Endpoint: http://localhost:8768" "INFO"
                Start-Sleep -Seconds 3
                
                if (-not (Get-Process -Id $MemosProc.Id -ErrorAction SilentlyContinue)) {
                    Write-Log "  [-] memOS.MCP exited unexpectedly!" "ERROR"
                    $MemosProc = $null
                }
            } catch {
                Pop-Location
                Write-Log "  [-] Failed to start memOS.MCP: $($_.Exception.Message)" "ERROR"
            }
        }
    } else {
        Write-Log "  [!] memOS.MCP not found at: $MemosPath" "WARN"
    }
    Write-Log ""
}

# --- 4. START OMEGAKG FULL STACK ---
$OmegaKGProcs = @{}
if (-not $SkipOmegaKG) {
    Write-Log "========================================" "INFO"
    Write-Log "Starting OmegaKG Full Stack" "INFO"
    Write-Log "========================================" "INFO"
    
    $OmegaKGPath = Join-Path $ProjectRoot "Omega_KG_stable"
    $OmegaKGScript = Join-Path $OmegaKGPath "scripts\start_full_stack.ps1"
    
    if (Test-Path $OmegaKGScript) {
        try {
            Push-Location $OmegaKGPath
            
            $OmegaKGArgs = @{
                FilePath = "powershell.exe"
                ArgumentList = "-NoProfile -ExecutionPolicy Bypass -File `"$OmegaKGScript`" $(if ($SkipCleanup) {'-SkipCleanup'} else {''}) $(if ($ShowConsole) {'-ShowConsole'} else {''}) $(if ($Persistent) {'-Persistent'} else {''})"
                WindowStyle = $WindowStyle
                PassThru = $true
                WorkingDirectory = $OmegaKGPath
            }
            
            $OmegaKGLauncher = Start-Process @OmegaKGArgs
            Pop-Location
            
            Write-Log "  [+] OmegaKG launcher started (PID: $($OmegaKGLauncher.Id))" "INFO"
            Write-Log "  [i] Waiting 8 seconds for services to initialize..." "INFO"
            Start-Sleep -Seconds 8
            
            # Capture references to started processes
            # Use CIM for properly reading CommandLines on Windows
            $AllPythonProcs = Get-CimInstance Win32_Process -Filter "Name like '%python%'" | Select-Object ProcessId, CommandLine

            $OmegaKGProcs['CaptureServer'] = $AllPythonProcs | Where-Object {
                $_.CommandLine -like "*omega_kg.capture_server*"
            } | Select-Object -First 1
            
            $OmegaKGProcs['EmbeddingWorker'] = $AllPythonProcs | Where-Object {
                $_.CommandLine -like "*omega_kg.workers.embedding_worker*"
            } | Select-Object -First 1
            
            $OmegaKGProcs['VectorWorker'] = $AllPythonProcs | Where-Object {
                $_.CommandLine -like "*omega_kg.workers.vector_index_worker*"
            } | Select-Object -First 1

            $OmegaKGProcs['ConversationWorker'] = $AllPythonProcs | Where-Object {
                $_.CommandLine -like "*omega_kg.workers.conversation_worker*"
            } | Select-Object -First 1
            
            
            if ($OmegaKGProcs['CaptureServer']) {
                Write-Log "  [+] Capture Server running (PID: $($OmegaKGProcs['CaptureServer'].ProcessId))" "INFO"
            }
            if ($OmegaKGProcs['EmbeddingWorker']) {
                Write-Log "  [+] Embedding Worker running (PID: $($OmegaKGProcs['EmbeddingWorker'].ProcessId))" "INFO"
            }
            if ($OmegaKGProcs['VectorWorker']) {
                Write-Log "  [+] Vector Index Worker running (PID: $($OmegaKGProcs['VectorWorker'].ProcessId))" "INFO"
            }
            if ($OmegaKGProcs['ConversationWorker']) {
                Write-Log "  [+] Conversation Worker running (PID: $($OmegaKGProcs['ConversationWorker'].ProcessId))" "INFO"
            }
            
        } catch {
            Pop-Location
            Write-Log "  [-] Failed to start OmegaKG: $($_.Exception.Message)" "ERROR"
        }
    } else {
        Write-Log "  [!] OmegaKG not found at: $OmegaKGPath" "WARN"
    }
    Write-Log ""
}

# --- 4B. START LOG WATCHDOG ---
$LogWatchdogProc = $null
if (-not $SkipOmegaKG) {
    Write-Log "========================================" "INFO"
    Write-Log "Starting Log Watchdog" "INFO"
    Write-Log "========================================" "INFO"
    
    $OmegaKGPath = Join-Path $ProjectRoot "Omega_KG_stable"
    $WatchdogScriptRel = "scripts/maintenance/log_watchdog.py"
    $FullWatchdogPath = Join-Path $OmegaKGPath $WatchdogScriptRel
    
    if (Test-Path $FullWatchdogPath) {
        # Check if already running
        $ExistingWatchdog = Get-CimInstance Win32_Process -Filter "Name like '%python%'" | Where-Object {
            $_.CommandLine -like "*log_watchdog.py*"
        } | Select-Object -First 1
        
        if ($ExistingWatchdog) {
            Write-Log "  [i] Log Watchdog already running (PID: $($ExistingWatchdog.ProcessId))" "INFO"
            $LogWatchdogProc = Get-Process -Id $ExistingWatchdog.ProcessId -ErrorAction SilentlyContinue
        } else {
            try {
                Push-Location $OmegaKGPath
                $WatchdogLog = Join-Path $LogDir "log_watchdog_$Time.log"
                $WatchdogErrLog = Join-Path $LogDir "log_watchdog_$Time.err.log"
                
                $PoetryCommand = Get-Command poetry -ErrorAction SilentlyContinue
                $SystemPython = "C:\Program Files\Python312\python.exe"

                if ($PoetryCommand) {
                    $WatchdogExecutor = $PoetryCommand.Source
                    $WatchdogArgsList = "run python $WatchdogScriptRel"
                } elseif (Test-Path $SystemPython) {
                    $WatchdogExecutor = $SystemPython
                    $WatchdogArgsList = "-m poetry run python $WatchdogScriptRel"
                } else {
                    $WatchdogExecutor = "python"
                    $WatchdogArgsList = "-m poetry run python $WatchdogScriptRel"
                }

                $WatchdogArgs = @{
                    FilePath = $WatchdogExecutor
                    ArgumentList = $WatchdogArgsList
                    WindowStyle = $WindowStyle
                    PassThru = $true
                    WorkingDirectory = $OmegaKGPath
                }
                
                if (-not $ShowConsole) {
                    $WatchdogArgs['RedirectStandardOutput'] = $WatchdogLog
                    $WatchdogArgs['RedirectStandardError'] = $WatchdogErrLog
                }
                
                $LogWatchdogProc = Start-Process @WatchdogArgs
                Pop-Location
                
                Write-Log "  [+] Log Watchdog started (PID: $($LogWatchdogProc.Id))" "INFO"
                Start-Sleep -Seconds 2
                
            } catch {
                Pop-Location
                Write-Log "  [-] Failed to start Log Watchdog: $($_.Exception.Message)" "ERROR"
            }
        }
    } else {
        Write-Log "  [!] Log Watchdog not found at: $FullWatchdogPath" "WARN"
    }
    Write-Log ""
}

# --- 5. START INGEST-LLM.AS ---
$IngestProcs = @{}
if (-not $SkipIngestLLM) {
    Write-Log "========================================" "INFO"
    Write-Log "Starting InGest-LLM.as" "INFO"
    Write-Log "========================================" "INFO"
    
    $IngestPath = Join-Path $ProjectRoot "InGest-LLM.as"
    $IngestScript = Join-Path $IngestPath "scripts\start_ingest_llm.ps1"
    
    if (Test-Path $IngestScript) {
        try {
            Push-Location $IngestPath
            
            $IngestArgs = @{
                FilePath = "powershell.exe"
                ArgumentList = "-NoProfile -ExecutionPolicy Bypass -File `"$IngestScript`" $(if ($ShowConsole) {'-ShowConsole'} else {''}) $(if ($Persistent) {'-Persistent'} else {''})"
                WindowStyle = $WindowStyle
                PassThru = $true
                WorkingDirectory = $IngestPath
            }
            
            $IngestLauncher = Start-Process @IngestArgs
            Pop-Location
            
            Write-Log "  [+] InGest-LLM.as launcher started (PID: $($IngestLauncher.Id))" "INFO"
            Write-Log "  [i] Waiting 12 seconds for services to initialize..." "INFO"
            Start-Sleep -Seconds 12
            
            # Capture references
            $IngestPythonProcs = Get-CimInstance Win32_Process -Filter "Name like '%python%' OR Name like '%uvicorn%'" | Select-Object ProcessId, CommandLine
            
            $IngestProcs['Uvicorn'] = $IngestPythonProcs | Where-Object {
                $_.CommandLine -like "*uvicorn*ingest_llm_as.main*"
            } | Select-Object -First 1
            
            $IngestProcs['Cloudflared'] = Get-CimInstance Win32_Process -Filter "Name like '%cloudflared%'" | Where-Object {
                $_.CommandLine -like "*valhalla-gateway*" -or $_.CommandLine -like "*tunnel*"
            } | Select-Object -First 1
            
            if ($IngestProcs['Uvicorn']) {
                Write-Log "  [+] Uvicorn API running (PID: $($IngestProcs['Uvicorn'].ProcessId))" "INFO"
                Write-Log "  [+] Endpoint: http://localhost:8766" "INFO"
            }
            if ($IngestProcs['Cloudflared']) {
                Write-Log "  [+] Cloudflared Tunnel running (PID: $($IngestProcs['Cloudflared'].Id))" "INFO"
            }
            
        } catch {
            Pop-Location
            Write-Log "  [-] Failed to start InGest-LLM.as: $($_.Exception.Message)" "ERROR"
        }
    } else {
        Write-Log "  [!] InGest-LLM.as not found at: $IngestPath" "WARN"
    }
    Write-Log ""
}

# --- 6. START CORTEXBRIDGE ---
$CortexProc = $null
if (-not $SkipCortexBridge) {
    Write-Log "========================================" "INFO"
    Write-Log "Starting CortexBridge (Frontend)" "INFO"
    Write-Log "========================================" "INFO"
    
    $CortexPath = Join-Path $ProjectRoot "CortexBridge"
    
    if (Test-Path $CortexPath) {
        # Check node/npm
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            # Check if likely already running (port check)
            $cortexPortTest = Test-NetConnection -ComputerName localhost -Port 6001 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
            
            if ($cortexPortTest.TcpTestSucceeded) {
                Write-Log "  [i] CortexBridge likely running (Port 6001 active)" "INFO"
            } else {
                try {
                    Push-Location $CortexPath
                    $CortexLog = Join-Path $LogDir "cortex_$Time.log"
                    $CortexErrLog = Join-Path $LogDir "cortex_$Time.err.log"
                    
                    Write-Log "  [+] Launching 'npm run dev'..." "INFO"
                    
                    $CortexArgs = @{
                        FilePath = "npm.cmd"
                        ArgumentList = "run dev"
                        WindowStyle = $WindowStyle
                        PassThru = $true
                        WorkingDirectory = $CortexPath
                    }
                    
                    if (-not $ShowConsole) {
                        $CortexArgs['RedirectStandardOutput'] = $CortexLog
                        $CortexArgs['RedirectStandardError'] = $CortexErrLog
                    }
                    
                    $CortexProc = Start-Process @CortexArgs
                    Pop-Location
                    
                    Write-Log "  [+] CortexBridge started (PID: $($CortexProc.Id))" "INFO"
                    Write-Log "  [i] Waiting 5 seconds for Vite to initialize..." "INFO"
                    Start-Sleep -Seconds 5
                    
                    if (-not (Get-Process -Id $CortexProc.Id -ErrorAction SilentlyContinue)) {
                        Write-Log "  [-] CortexBridge exited unexpectedly!" "ERROR"
                        $CortexProc = $null
                    }
                } catch {
                    Pop-Location
                    Write-Log "  [-] Failed to start CortexBridge: $($_.Exception.Message)" "ERROR"
                }
            }
        } else {
            Write-Log "  [!] npm not found in PATH" "WARN"
        }
    } else {
        Write-Log "  [!] CortexBridge not found at: $CortexPath" "WARN"
    }
    Write-Log ""
}

# --- 7. SUMMARY ---
Write-Log "========================================" "INFO"
Write-Log "OmegaKG Ecosystem Status" "INFO"
Write-Log "========================================" "INFO"

if ($MemosProc) {
    Write-Log "  ✅ memOS.MCP:           http://localhost:8768" "INFO"
} else {
    Write-Log "  ❌ memOS.MCP:           Not running" "WARN"
}

if ($OmegaKGProcs['CaptureServer']) {
    Write-Log "  ✅ OmegaKG Capture:     http://localhost:8765" "INFO"
} else {
    Write-Log "  ❌ OmegaKG Capture:     Not running" "WARN"
}

if ($OmegaKGProcs['EmbeddingWorker']) {
    Write-Log "  ✅ Embedding Worker:    Running" "INFO"
} else {
    Write-Log "  ⚠️  Embedding Worker:    Not running" "WARN"
}

if ($OmegaKGProcs['VectorWorker']) {
    Write-Log "  ✅ Vector Worker:       Running" "INFO"
} else {
    Write-Log "  ⚠️  Vector Worker:       Not running" "WARN"
}

if ($OmegaKGProcs['ConversationWorker']) {
    Write-Log "  ✅ Conversation Worker: Running" "INFO"
} else {
    Write-Log "  ⚠️  Conversation Worker: Not running" "WARN"
}

if ($IngestProcs['Uvicorn']) {
    Write-Log "  ✅ InGest-LLM API:      http://localhost:8766" "INFO"
} else {
    Write-Log "  ❌ InGest-LLM API:      Not running" "WARN"
}

if ($IngestProcs['Cloudflared']) {
    Write-Log "  ✅ Cloudflared Tunnel:  Running" "INFO"
} else {
    Write-Log "  ⚠️  Cloudflared Tunnel:  Not running" "WARN"
}

if ($LogWatchdogProc) {
    Write-Log "  ✅ Log Watchdog:        Running" "INFO"
} else {
    Write-Log "  ⚠️  Log Watchdog:        Not running" "WARN"
}

if ($CortexProc -or (Test-NetConnection -ComputerName localhost -Port 6001 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue).TcpTestSucceeded) {
    Write-Log "  ✅ CortexBridge:        http://localhost:6001" "INFO"
} else {
    Write-Log "  ❌ CortexBridge:        Not running" "WARN"
}

Write-Log "========================================" "INFO"
Write-Log ""

# Open CortexBridge dashboard in default browser (Last action)
if (-not $SkipCortexBridge) {
    Write-Log "Opening Dashboard: http://localhost:6001" "INFO"
    Start-Process "http://localhost:6001"
}

# --- 8. PERSISTENCE LOOP (MASTER WATCHDOG) ---
if ($Persistent) {
    Write-Log "MASTER WATCHDOG ACTIVE: Monitoring all services every 15s." "INFO"
    Write-Log "Press Ctrl+C to stop all services." "INFO"
    Write-Log ""
    
    while ($true) {
        Start-Sleep -Seconds 15
        
        $RestartTime = Get-Date -Format "HH:mm:ss"
        
        # Note: Individual service scripts handle their own restarts
        # This is just high-level monitoring
        
        # Check memOS.MCP - use process query instead of HasExited (launcher exits after spawning server)
        $memosCheck = Get-CimInstance Win32_Process -Filter "Name like '%python%'" | Where-Object { $_.CommandLine -like "*memos_mcp*server*" }
        if (-not $memosCheck) {
            Write-Log "[$RestartTime] memOS.MCP exited unexpectedly! Restarting..." "WARN"
            
            # 1. Kill any zombies
            Kill-TargetProcess "memos_mcp" "memOS.MCP (Zombie)"
            
            # 2. Restart
            try {
                if ($script:MemosExecutor) {
                     $MemosArgs = @{
                        FilePath = $script:MemosExecutor
                        ArgumentList = $script:MemosArgsList
                        WindowStyle = $WindowStyle
                        PassThru = $true
                        WorkingDirectory = (Join-Path $ProjectRoot "memos.MCP")
                    }
                    if (-not $ShowConsole) {
                        $MemosArgs['RedirectStandardOutput'] = (Join-Path $LogDir "memos_mcp_$RestartTime.log".Replace(":","-"))
                        $MemosArgs['RedirectStandardError'] = (Join-Path $LogDir "memos_mcp_$RestartTime.err.log".Replace(":","-"))
                    }
                    
                    $MemosProc = Start-Process @MemosArgs
                    Write-Log "  [+] memOS.MCP restarted (PID: $($MemosProc.Id))" "INFO"
                } else {
                    Write-Log "  [-] Cannot restart memOS.MCP: Executor info missing." "ERROR"
                }
            } catch {
                Write-Log "  [-] Failed to restart memOS.MCP: $($_.Exception.Message)" "ERROR"
            }
        }

        # Retrieve all python/uvicorn processes once to minimize WMI calls
        $AllPythonProcs = Get-CimInstance Win32_Process -Filter "Name like '%python%' OR Name like '%uvicorn%'" | Select-Object ProcessId, CommandLine

        # Verify OmegaKG Capture Server
        $captureCheck = $AllPythonProcs | Where-Object { $_.CommandLine -like "*omega_kg.capture_server*" }
        if (-not $captureCheck) {
            Write-Log "[$RestartTime] OmegaKG Capture Server is down!" "WARN"
        }

        # Verify InGest-LLM Uvicorn
        $uvicornCheck = $AllPythonProcs | Where-Object { $_.CommandLine -like "*uvicorn*ingest_llm_as*" }
        if (-not $uvicornCheck) {
            Write-Log "[$RestartTime] InGest-LLM Uvicorn is down!" "WARN"
        }

        # Verify Log Watchdog
        if ($LogWatchdogProc) {
             if ($LogWatchdogProc.HasExited) {
                Write-Log "[$RestartTime] Log Watchdog exited unexpectedly!" "WARN"
                $LogWatchdogProc = $null
             }
        }

        # Verify CortexBridge (npm run dev usually spawns node)
        # We'll rely on our process handle if we started it
        if ($CortexProc) {
            if ($CortexProc.HasExited) {
                Write-Log "[$RestartTime] CortexBridge exited unexpectedly!" "ERROR"
                $CortexProc = $null
            }
        }
    }
} else {
    Write-Log "Ecosystem startup complete." "INFO"
    Write-Log "All services are running independently." "INFO"
    Write-Log "Use -Persistent flag for master watchdog monitoring." "INFO"
}
