<#
.SYNOPSIS
    Soma "Distributed Brain" Startup Orchestrator v2.4 (WT Fix)

.DESCRIPTION
    Launches the Soma ecosystem.
    Fixes 0x80070002 by removing fragile WT profile dependency and using explicit command lines.
    Fixes ModuleNotFoundError by ensuring PYTHONPATH is absolute.
#>

[CmdletBinding()]
param(
    [switch]$SkipHealthCheck,
    [switch]$StateLayerOnly,
    [switch]$SkipInterface
)

$ErrorActionPreference = "Stop"
# Ensure we resolve the root correctly.
$REPO_ROOT = "$PSScriptRoot\.." | Resolve-Path

# --- CONFIGURATION ---
$Ports = @{
    Postgres  = 6000
    Neo4jHTTP = 7474
    Redis     = 6380
    OmegaKG   = 8765
    memOS     = 8768
    InGest    = 3000
    Cortex    = 6001
}

# --- HELPER FUNCTIONS ---

function Write-Status {
    param([string]$Message, [string]$Color = "Cyan", [string]$Icon = "ℹ")
    $Timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$Timestamp] $Icon $Message" -ForegroundColor $Color
}

function Test-PortListening {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("localhost", $Port)
        $tcp.Close()
        return $true
    }
    catch { return $false }
}

function Start-ServiceTab {
    param(
        [string]$ServiceName,
        [string]$WorkingDirectory,
        [string]$Command,
        [string]$Color = "Cyan",
        [string]$RepoRoot = $REPO_ROOT
    )
    
    Write-Status "Launching $ServiceName..." "DarkCyan" "🚀"
    
    if (-not (Test-Path $WorkingDirectory)) {
        Write-Status "Directory not found: $WorkingDirectory" "Red" "✗"
        return
    }

    # 1. Create a temporary startup script for this service
    # We strip special chars for filename
    $SafeName = $ServiceName -replace '[^a-zA-Z0-9]', ''
    $TempScriptPath = "$env:TEMP\soma_launch_$SafeName.ps1"
    
    # We bake the PYTHONPATH logic right into the script to fix ModuleNotFoundError
    # IMPORTANT: Use .Path property of Resolve-Path object to get string
    $RootPathStr = $RepoRoot.Path
    
    $ScriptContent = @"
`$ErrorActionPreference = 'Stop'
[Console]::Title = '$ServiceName'
Write-Host '🧠 $ServiceName Starting...' -ForegroundColor $Color
Write-Host '📂 Dir: $WorkingDirectory' -ForegroundColor DarkGray

# Set PYTHONPATH so Python can find 'omega_kg' module from root
if ('$SafeName' -match 'OmegaKG|memOS') {
    `$env:PYTHONPATH = '$RootPathStr;' + `$env:PYTHONPATH
    Write-Host "🐍 PYTHONPATH set: $RootPathStr" -ForegroundColor DarkGray
}

Set-Location '$WorkingDirectory'

try {
    # Execute the actual command
    # We use Invoke-Expression to handle the command string execution
    Write-Host "Running: $Command" -ForegroundColor DarkGray
    Invoke-Expression '$Command'
} catch {
    Write-Error "Failed to start service: `$_"
}

Read-Host "Press Enter to exit..."
"@
    
    Set-Content -Path $TempScriptPath -Value $ScriptContent
    
    # 2. Launch the script
    # Strategy: Use Start-Process directly on pwsh/powershell.
    # If WT exists, use it to wrap the shell.
    
    if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
        # Fix 0x80070002: Do NOT use -p (Profile). Just run the command.
        # Syntax: wt.exe new-tab --title "Name" command args...
        # We use powershell.exe -NoExit -File ... as the command
        Start-Process wt.exe -ArgumentList "new-tab", "--title", "$ServiceName", "powershell.exe", "-NoExit", "-File", "$TempScriptPath"
    }
    else {
        # Fallback to standard PowerShell window
        Start-Process powershell.exe -ArgumentList "-NoExit", "-File", "$TempScriptPath"
    }
}

# --- PHASE 1: PRE-FLIGHT ---
Write-Status "PHASE 1: PRE-FLIGHT DIAGNOSTICS" "Magenta" "🔎"

# 1. Dependencies
foreach ($cmd in @("docker", "node")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Status "$cmd missing" "Red" "✗"
        exit 1
    }
}

# 2. Python Environment Logic
$VenvPython = "$REPO_ROOT\.venv\Scripts\python.exe"
$VenvDagster = "$REPO_ROOT\.venv\Scripts\dagster.exe"

if (Test-Path $VenvPython) {
    Write-Status "Using Virtual Environment (.venv)" "Green" "✓"
    # Important: We must wrap paths in quotes for the generated script string
    $PyCmd = "& '$VenvPython'"
    $DagsterCmd = "& '$VenvDagster'"
}
elseif (Get-Command poetry -ErrorAction SilentlyContinue) {
    Write-Status "Using Poetry" "Yellow" "⚠"
    $PyCmd = "poetry run python"
    $DagsterCmd = "poetry run dagster"
}
else {
    Write-Status "No Python environment found" "Red" "✗"
    exit 1
}

# --- PHASE 2: STATE LAYER ---
Write-Status "PHASE 2: STATE LAYER (DOCKER)" "Magenta" "🐳"
Set-Location $REPO_ROOT

# Reset WINNAT if Admin
if (([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        Stop-Service "HKLM\SYSTEM\CurrentControlSet\Services\WinNat" -ErrorAction SilentlyContinue
        Start-Service "HKLM\SYSTEM\CurrentControlSet\Services\WinNat" -ErrorAction SilentlyContinue
    }
    catch {}
}

docker-compose up -d postgres neo4j redis

if (-not $SkipHealthCheck) {
    $MaxRetries = 30
    foreach ($Service in @("Postgres", "Neo4jHTTP", "Redis")) {
        $Port = $Ports[$Service]
        Write-Host "  Waiting for $Service ($Port)..." -NoNewline
        $Retry = 0
        while (-not (Test-PortListening $Port)) {
            if ($Retry -ge $MaxRetries) { Write-Host " TIMEOUT!" -ForegroundColor Red; exit 1 }
            Start-Sleep -Seconds 2
            $Retry++
            Write-Host "." -NoNewline
        }
        Write-Host " OK" -ForegroundColor Green
    }
}

if ($StateLayerOnly) { exit 0 }

# --- PHASE 3: LOGIC LAYER ---
Write-Status "PHASE 3: LOGIC LAYER (NATIVE)" "Magenta" "🧠"

# 1. memOS (Hands)
Start-ServiceTab -ServiceName "memOS (Hands)" `
    -WorkingDirectory "$REPO_ROOT\memOS" `
    -Command "$PyCmd -m uvicorn omega_kg.memos.main:app --host 0.0.0.0 --port $($Ports.memOS) --reload" `
    -Color "Green"

Start-Sleep -Seconds 2

# 2. OmegaKG (Brain)
Start-ServiceTab -ServiceName "OmegaKG (Brain)" `
    -WorkingDirectory "$REPO_ROOT\OmegaKG" `
    -Command "$PyCmd -m omega_kg.main --host 0.0.0.0 --port $($Ports.OmegaKG) --reload" `
    -Color "Magenta"

Start-Sleep -Seconds 2

# 3. InGest (Stomach)
Start-ServiceTab -ServiceName "InGest (Stomach)" `
    -WorkingDirectory "$REPO_ROOT\InGest" `
    -Command "$DagsterCmd dev -h 0.0.0.0 -p $($Ports.InGest)" `
    -Color "Yellow"

# --- PHASE 4: INTERFACE LAYER ---
if (-not $SkipInterface) {
    Write-Status "PHASE 4: INTERFACE LAYER" "Magenta" "💻"
    Start-ServiceTab -ServiceName "Cortex (Executive)" `
        -WorkingDirectory "$REPO_ROOT\Cortex" `
        -Command "npm run dev -- --port $($Ports.Cortex) --host 0.0.0.0" `
        -Color "Blue"
}

Write-Status "SYSTEM ONLINE" "Green" "⚡"