# Omega Full Stack Launcher (v2.5 Hookdeck-Fixed)
# -------------------------
# Purpose: Orchestrates Capture Server (Uvicorn), Hookdeck Gateway, and GitHub Listener.
# Usage:
#   ./start_full_stack.ps1                      -> Production (Hidden Windows, Log to Files, Manual Hookdeck)
#   ./start_full_stack.ps1 -ShowConsole        -> Debugging (Visible Windows, Auto-starts Hookdeck in separate windows)
#   ./start_full_stack.ps1 -SkipCleanup        -> Skip cleanup (useful if cleanup was already run)
#   ./start_full_stack.ps1 -SkipCleanup -Persistent -> Skip cleanup and keep processes alive with watchdog
#
# With -ShowConsole: Hookdeck listeners automatically start in separate console windows for monitoring
# Without -ShowConsole: Hookdeck listeners must be started manually (production mode)
#
# v2.5 Changes:
# - Fixed to use hookdeck.exe directly (Windows binary) instead of shell wrapper
# - Fixed command syntax to use "listen <port> <source>" format
# - Both Linear and GitHub listeners use port 8765 (Hookdeck limitation)
#

param (
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$EnvFile = ".env",
    [switch]$ShowConsole,
    [switch]$Persistent,
    [switch]$SkipCleanup
    )

$ErrorActionPreference = "Stop"

# --- 1. SETUP LOGGING & WINDOW MODES ---
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Time = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$CaptureLog = Join-Path $LogDir "capture_server_$Time.log"
$CaptureErrLog = Join-Path $LogDir "capture_server_$Time.err.log"
$HookdeckLog = Join-Path $LogDir "hookdeck_$Time.log"
$HookdeckErrLog = Join-Path $LogDir "hookdeck_$Time.err.log"

if ($ShowConsole) {
    Write-Warning "[$Time] DEBUG MODE: Windows will be visible. Logs streaming to screen (NOT files)."
    $WindowStyle = "Normal"
    $LogArgs_Capture = @{}
    $LogArgs_Hookdeck = @{}
} else {
    Write-Output "[$Time] PRODUCTION MODE: Windows hidden. Logs written to $LogDir"
    $WindowStyle = "Hidden"
    $LogArgs_Capture = @{
        RedirectStandardOutput = $CaptureLog
        RedirectStandardError = $CaptureErrLog
    }
    # For Hookdeck, always use Normal window style to allow manual interaction
    $LogArgs_Hookdeck = @{}
}

# --- 2. SECRET INJECTION & CLEANUP ---
if (-not $SkipCleanup) {
    Write-Output "[$Time] Cleaning up existing processes..."
    & (Join-Path $PSScriptRoot "cleanup_before_start.ps1")
} else {
    Write-Output "[$Time] Skipping cleanup (SkipCleanup flag set)."
}

Write-Output "[$Time] Ensuring databases are running..."
& (Join-Path $PSScriptRoot "start-database.ps1")

$EnvPath = Join-Path $ProjectRoot $EnvFile
if (Test-Path $EnvPath) {
    Write-Output "[$Time] Loading .env..."
    Get-Content $EnvPath | Where-Object { $_ -match '=' -and $_ -notmatch '^#' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
    }
}

# Hookdeck check removed
# if (-not $env:HOOKDECK_API_KEY) {
#     Write-Error "FATAL: HOOKDECK_API_KEY is missing. Aborting."
#     exit 1
# }

# --- 3. START CAPTURE SERVER (UVICORN) ---
$env:HOST = "0.0.0.0"
$env:PORT = "8765"

Write-Output "[$Time] Checking Capture Server status..."
Write-Output "[$Time] Capture Server will bind to: $env:HOST`:$env:PORT"
$PoetryCommand = Get-Command poetry -ErrorAction SilentlyContinue
$SystemPython = "C:\Program Files\Python312\python.exe"

if ($PoetryCommand) {
    $PoetryPath = $PoetryCommand.Source
    $PoetryPrefix = ""
} elseif (Test-Path $SystemPython) {
    $PoetryPath = $SystemPython
    $PoetryPrefix = "-m poetry "
} else {
    $PoetryPath = "python"
    $PoetryPrefix = "-m poetry "
}

$PoetryRunArgs = "${PoetryPrefix}run python -m omega_kg.capture_server --host $env:HOST"

# Check if Poetry process with capture_server is already running
$ExistingPoetry = Get-Process -Name "poetry" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*capture_server*"
}

$CaptureProc = $null
if ($ExistingPoetry) {
    Write-Output "   [i] Capture Server already running (PID: $($ExistingPoetry.Id)). Skipping start."
    $CaptureProc = $ExistingPoetry
} else {
    Write-Output "[$Time] Launching Capture Server..."
    try {
        $CaptureProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryRunArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
        Write-Output "   [+] Capture Server started (PID: $($CaptureProc.Id))."
        Write-Output "[$Time] Waiting 5 seconds for Capture Server to initialize..."
        Start-Sleep -Seconds 5
        
        # Verify process is still running
        if (-not (Get-Process -Id $CaptureProc.Id -ErrorAction SilentlyContinue)) {
            Write-Error "   [-] Capture Server process exited unexpectedly after 5 seconds!"
            $CaptureProc = $null
        } else {
            Write-Output "[$Time] Capture Server is running and ready."
        }
    } catch {
        Write-Error "   [-] Failed to start Capture Server: $($_.Exception.Message)"
    }
}

# --- 5. START EMBEDDING WORKER (Saga Weaver) ---
Write-Output "[$Time] Checking Embedding Worker status..."
$WorkerProc = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*omega_kg.workers.embedding_worker*"
}

$PoetryWorkerArgs = "${PoetryPrefix}run python -m omega_kg.workers.embedding_worker"

if ($WorkerProc) {
    Write-Output "   [i] Embedding Worker already running (PID: $($WorkerProc.Id)). Skipping start."
} else {
    Write-Output "[$Time] Launching Embedding Worker..."
    try {
        $WorkerProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryWorkerArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
        Write-Output "   [+] Embedding Worker started (PID: $($WorkerProc.Id))."
    } catch {
        Write-Error "   [-] Failed to start Embedding Worker: $($_.Exception.Message)"
    }
}

# --- 5B. START VECTOR INDEX WORKER ---
Write-Output "[$Time] Checking Vector Index Worker status..."
$VectorWorkerProc = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*omega_kg.workers.vector_index_worker*"
}

$PoetryVectorWorkerArgs = "${PoetryPrefix}run python -m omega_kg.workers.vector_index_worker"

if ($VectorWorkerProc) {
    Write-Output "   [i] Vector Index Worker already running (PID: $($VectorWorkerProc.Id)). Skipping start."
} else {
    Write-Output "[$Time] Launching Vector Index Worker..."
    try {
        $VectorWorkerProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryVectorWorkerArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
        Write-Output "   [+] Vector Index Worker started (PID: $($VectorWorkerProc.Id))."
    } catch {
        Write-Error "   [-] Failed to start Vector Index Worker: $($_.Exception.Message)"
    }
}

# --- 5C. START CONVERSATION WORKER (Workhorse) ---
Write-Output "[$Time] Checking Conversation Worker status..."
$ConversationWorkerProc = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*omega_kg.workers.conversation_worker*"
}

$PoetryConvWorkerArgs = "${PoetryPrefix}run python -m omega_kg.workers.conversation_worker"

if ($ConversationWorkerProc) {
    Write-Output "   [i] Conversation Worker already running (PID: $($ConversationWorkerProc.Id)). Skipping start."
} else {
    Write-Output "[$Time] Launching Conversation Worker..."
    try {
        $ConversationWorkerProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryConvWorkerArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
        Write-Output "   [+] Conversation Worker started (PID: $($ConversationWorkerProc.Id))."
    } catch {
        Write-Error "   [-] Failed to start Conversation Worker: $($_.Exception.Message)"
    }
}


# --- 6. TERMINAL HOOK SETUP ---
$HookScriptPath = Join-Path $ProjectRoot "scripts" "Invoke-OmegaCapture.ps1"
if (Test-Path $HookScriptPath) {
    Write-Output "[$Time] Sourcing Terminal Capture Hook..."
    Write-Output "   [!] To enable capture in THIS session, run: . '$HookScriptPath'"
    Write-Output "   [i] The hook will be auto-loaded if added to `$PROFILE"
}

# --- 7. PERSISTENCE LOOP (WATCHDOG) ---
if ($Persistent) {
    Write-Output "[$Time] WATCHDOG ACTIVE: Monitoring Services every 10s. Press Ctrl+C to stop."
    while ($true) {
        Start-Sleep -Seconds 10
        
        # Check Capture Server
        if ($null -eq $CaptureProc -or $CaptureProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Capture Server is down. Restarting..."
            try {
                $CaptureProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryRunArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
                Write-Output "   [+] Capture Server restarted (PID: $($CaptureProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Capture Server: $($_.Exception.Message)"
            }
        }

        # Check Embedding Worker
        if ($null -eq $WorkerProc -or $WorkerProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Embedding Worker is down. Restarting..."
            try {
                $WorkerProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryWorkerArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
                Write-Output "   [+] Embedding Worker restarted (PID: $($WorkerProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Embedding Worker: $($_.Exception.Message)"
            }
        }

        # Check Vector Index Worker
        if ($null -eq $VectorWorkerProc -or $VectorWorkerProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Vector Index Worker is down. Restarting..."
            try {
                $VectorWorkerProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryVectorWorkerArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
                Write-Output "   [+] Vector Index Worker restarted (PID: $($VectorWorkerProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Vector Index Worker: $($_.Exception.Message)"
            }
        }

        # Check Conversation Worker
        if ($null -eq $ConversationWorkerProc -or $ConversationWorkerProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Conversation Worker is down. Restarting..."
            try {
                $ConversationWorkerProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryConvWorkerArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
                Write-Output "   [+] Conversation Worker restarted (PID: $($ConversationWorkerProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Conversation Worker: $($_.Exception.Message)"
            }
        }
    }
} else {
    Write-Output "[$Time] Sequence complete. Processes are running in background."
}
