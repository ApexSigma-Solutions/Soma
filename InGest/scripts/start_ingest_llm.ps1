# InGest-LLM.as Full Stack Launcher
# -------------------------
# Purpose: Orchestrates Uvicorn API Server and Cloudflared Tunnel Gateway
# Usage:
#   ./start_ingest_llm.ps1                     -> Production (Hidden Windows, Log to Files)
#   ./start_ingest_llm.ps1 -ShowConsole       -> Debugging (Visible Windows)
#   ./start_ingest_llm.ps1 -Persistent        -> Keep processes alive with watchdog
#   ./start_ingest_llm.ps1 -ShowConsole -Persistent -> Debug mode with watchdog
#

param (
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$EnvFile = ".env",
    [switch]$ShowConsole,
    [switch]$Persistent
)

$ErrorActionPreference = "Stop"

# --- 1. SETUP LOGGING & WINDOW MODES ---
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Time = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$UvicornLog = Join-Path $LogDir "uvicorn_$Time.log"
$UvicornErrLog = Join-Path $LogDir "uvicorn_$Time.err.log"
$CloudflaredLog = Join-Path $LogDir "cloudflared_$Time.log"
$CloudflaredErrLog = Join-Path $LogDir "cloudflared_$Time.err.log"

if ($ShowConsole) {
    Write-Warning "[$Time] DEBUG MODE: Windows will be visible."
    $WindowStyle = "Normal"
    $LogArgs_Uvicorn = @{}
    $LogArgs_Cloudflared = @{}
} else {
    Write-Output "[$Time] PRODUCTION MODE: Windows hidden. Logs written to $LogDir"
    $WindowStyle = "Hidden"
    $LogArgs_Uvicorn = @{
        RedirectStandardOutput = $UvicornLog
        RedirectStandardError = $UvicornErrLog
    }
    $LogArgs_Cloudflared = @{
        RedirectStandardOutput = $CloudflaredLog
        RedirectStandardError = $CloudflaredErrLog
    }
}

# --- 2. LOAD ENVIRONMENT ---
$EnvPath = Join-Path $ProjectRoot $EnvFile
if (Test-Path $EnvPath) {
    Write-Output "[$Time] Loading .env..."
    Get-Content $EnvPath | Where-Object { $_ -match '=' -and $_ -notmatch '^#' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
    }
}

# --- 3. BOOTSTRAP NLP DEPENDENCIES ---
Write-Output "[$Time] Bootstrapping NLP dependencies (Spacy + NLTK)..."
$BootstrapScript = Join-Path $ProjectRoot "bootstrap.py"

if (Test-Path $BootstrapScript) {
    try {
        $PoetryCommand = Get-Command poetry -ErrorAction SilentlyContinue
        $SystemPython = "C:\Program Files\Python312\python.exe"
        
        if ($PoetryCommand) {
            $BootstrapExecutor = $PoetryCommand.Source
            $BootstrapArgs = "run python bootstrap.py"
        } elseif (Test-Path $SystemPython) {
            $BootstrapExecutor = $SystemPython
            $BootstrapArgs = "-m poetry run python bootstrap.py"
        } else {
            $BootstrapExecutor = "python"
            $BootstrapArgs = "-m poetry run python bootstrap.py"
        }
        
        $BootstrapResult = Start-Process -FilePath $BootstrapExecutor `
            -ArgumentList $BootstrapArgs `
            -WorkingDirectory $ProjectRoot `
            -Wait `
            -PassThru `
            -NoNewWindow
        
        if ($BootstrapResult.ExitCode -eq 0) {
            Write-Output "   [✅] NLP dependencies verified/installed successfully"
        } else {
            Write-Warning "   [⚠️] Bootstrap completed with warnings (exit code: $($BootstrapResult.ExitCode))"
        }
    } catch {
        Write-Warning "   [⚠️] Bootstrap failed: $($_.Exception.Message)"
        Write-Output "   [i] Continuing anyway - service may fail if dependencies are missing"
    }
} else {
    Write-Output "   [i] Bootstrap script not found - skipping dependency check"
}

# --- 4. START UVICORN API SERVER ---
$UvicornPort = 8766
Write-Output "[$Time] Checking Uvicorn API Server status (port $UvicornPort)..."

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

# Set PYTHONPATH to include src/ directory for module resolution
$PythonPath = Join-Path $ProjectRoot "src"
[Environment]::SetEnvironmentVariable("PYTHONPATH", $PythonPath, "Process")
Write-Output "   [i] PYTHONPATH set to: $PythonPath"

$UvicornArgs = "run uvicorn ingest_llm_as.main:app --port $UvicornPort --reload"

# Check if Uvicorn is already running
$ExistingUvicorn = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*ingest_llm_as.main*"
}

$UvicornProc = $null
if ($ExistingUvicorn) {
    Write-Output "   [i] Uvicorn API Server already running (PID: $($ExistingUvicorn.Id)). Skipping start."
    $UvicornProc = $ExistingUvicorn
} else {
    Write-Output "[$Time] Launching Uvicorn API Server..."
    try {
        $UvicornProc = Start-Process -FilePath $PoetryPath `
            -ArgumentList $UvicornArgs `
            -WindowStyle $WindowStyle `
            -PassThru `
            -WorkingDirectory $ProjectRoot `
            @LogArgs_Uvicorn
        
        Write-Output "   [+] Uvicorn API Server started (PID: $($UvicornProc.Id))."
        Write-Output "[$Time] Waiting 3 seconds for Uvicorn to initialize..."
        Start-Sleep -Seconds 3
        
        # Verify process is still running
        if (-not (Get-Process -Id $UvicornProc.Id -ErrorAction SilentlyContinue)) {
            Write-Error "   [-] Uvicorn process exited unexpectedly!"
            $UvicornProc = $null
        } else {
            Write-Output "[$Time] Uvicorn API Server is running at http://localhost:$UvicornPort"
        }
    } catch {
        Write-Error "   [-] Failed to start Uvicorn: $($_.Exception.Message)"
    }
}

# --- 5. START CLOUDFLARED TUNNEL ---
Write-Output "[$Time] Checking Cloudflared Tunnel status..."

$CloudflaredPath = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $CloudflaredPath) {
    Write-Warning "   [!] cloudflared not found in PATH. Skipping tunnel start."
    Write-Output "   [i] Install from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
    $CloudflaredProc = $null
} else {
    # Check if cloudflared is already running
    $ExistingCloudflared = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*valhalla-gateway*"
    }

    $CloudflaredProc = $null
    if ($ExistingCloudflared) {
        Write-Output "   [i] Cloudflared Tunnel already running (PID: $($ExistingCloudflared.Id)). Skipping start."
        $CloudflaredProc = $ExistingCloudflared
    } else {
        Write-Output "[$Time] Launching Cloudflared Tunnel (valhalla-gateway)..."
        try {
            $CloudflaredArgs = "tunnel run --protocol http2 valhalla-gateway"
            
            $CloudflaredProc = Start-Process -FilePath $CloudflaredPath `
                -ArgumentList $CloudflaredArgs `
                -WindowStyle $WindowStyle `
                -PassThru `
                -WorkingDirectory (Join-Path $ProjectRoot "ingest-llm") `
                @LogArgs_Cloudflared
            
            Write-Output "   [+] Cloudflared Tunnel started (PID: $($CloudflaredProc.Id))."
            Write-Output "[$Time] Waiting 2 seconds for tunnel to connect..."
            Start-Sleep -Seconds 2
            
            # Verify process is still running
            if (-not (Get-Process -Id $CloudflaredProc.Id -ErrorAction SilentlyContinue)) {
                Write-Warning "   [-] Cloudflared process exited. Check configuration."
                $CloudflaredProc = $null
            } else {
                Write-Output "[$Time] Cloudflared Tunnel is running (valhalla-gateway)."
            }
        } catch {
            Write-Error "   [-] Failed to start Cloudflared: $($_.Exception.Message)"
        }
    }
}

# --- 6. SUMMARY ---
Write-Output ""
Write-Output "=" * 70
Write-Output "InGest-LLM.as Stack Status"
Write-Output "=" * 70
if ($UvicornProc) {
    Write-Output "  ✅ Uvicorn API:    http://localhost:$UvicornPort (PID: $($UvicornProc.Id))"
} else {
    Write-Output "  ❌ Uvicorn API:    Not running"
}
if ($CloudflaredProc) {
    Write-Output "  ✅ Cloudflared:    valhalla-gateway tunnel (PID: $($CloudflaredProc.Id))"
} else {
    Write-Output "  ⚠️  Cloudflared:    Not running"
}
Write-Output "=" * 70
Write-Output ""

# --- 7. PERSISTENCE LOOP (WATCHDOG) ---
if ($Persistent) {
    Write-Output "[$Time] WATCHDOG ACTIVE: Monitoring services every 10s. Press Ctrl+C to stop."
    while ($true) {
        Start-Sleep -Seconds 10
        
        # Check Uvicorn
        if ($null -eq $UvicornProc -or $UvicornProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Uvicorn API Server is down. Restarting..."
            try {
                $UvicornProc = Start-Process -FilePath $PoetryPath `
                    -ArgumentList $UvicornArgs `
                    -WindowStyle $WindowStyle `
                    -PassThru `
                    -WorkingDirectory $ProjectRoot `
                    @LogArgs_Uvicorn
                Write-Output "   [+] Uvicorn API Server restarted (PID: $($UvicornProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Uvicorn: $($_.Exception.Message)"
            }
        }
        
        # Check Cloudflared
        if ($CloudflaredPath -and ($null -eq $CloudflaredProc -or $CloudflaredProc.HasExited)) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Cloudflared Tunnel is down. Restarting..."
            try {
                $CloudflaredProc = Start-Process -FilePath $CloudflaredPath `
                    -ArgumentList "tunnel run --protocol http2 valhalla-gateway" `
                    -WindowStyle $WindowStyle `
                    -PassThru `
                    -WorkingDirectory (Join-Path $ProjectRoot "ingest-llm") `
                    @LogArgs_Cloudflared
                Write-Output "   [+] Cloudflared Tunnel restarted (PID: $($CloudflaredProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Cloudflared: $($_.Exception.Message)"
            }
        }
    }
} else {
    Write-Output "[$Time] Services are running. Use -Persistent flag for watchdog monitoring."
}
