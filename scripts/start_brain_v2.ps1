<#
.SYNOPSIS
    Soma "Distributed Brain" Startup Orchestrator v2.2 (Fixed)

.DESCRIPTION
    Launches the Soma ecosystem.
    Fixes 0x80070002 errors by simplifying process launching logic.
#>

[CmdletBinding()]
param(
    [switch]$SkipHealthCheck,
    [switch]$StateLayerOnly,
    [switch]$SkipInterface
)

$ErrorActionPreference = "Stop"
# Ensure we resolve the root correctly
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
        [string]$Color = "Cyan"
    )
    
    Write-Status "Launching $ServiceName..." "DarkCyan" "🚀"
    
    if (-not (Test-Path $WorkingDirectory)) {
        Write-Status "Directory not found: $WorkingDirectory" "Red" "✗"
        return
    }

    # Use powershell.exe which is guaranteed to exist on Windows
    $ShellExe = "powershell.exe"
    
    # Simple, robust startup command
    $StartupCmd = "Write-Host '🧠 $ServiceName Starting...' -ForegroundColor $Color; $Command"
    
    # Check for Windows Terminal
    if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
        # Launch in new WT tab
        # Note: We pass the directory to WT directly via -d
        Start-Process wt.exe -ArgumentList "new-tab", "--title", "$ServiceName", "-d", "$WorkingDirectory", "-p", "PowerShell", $ShellExe, "-NoExit", "-Command", "& {$StartupCmd}"
    }
    else {
        # Fallback to separate windows
        Start-Process $ShellExe -ArgumentList "-NoExit", "-Command", "cd '$WorkingDirectory'; $StartupCmd"
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
    $PyCmd = $VenvPython
    # Important: Quote the path if it has spaces, but usually for Start-Process args we need raw strings
    # We will handle quoting in the Command string passed to Start-ServiceTab
}
elseif (Get-Command poetry -ErrorAction SilentlyContinue) {
    Write-Status "Using Poetry" "Yellow" "⚠"
    $PyCmd = "poetry run python"
    $VenvDagster = "poetry run dagster" # Fallback variable name reuse
}
else {
    Write-Status "No Python environment found" "Red" "✗"
    exit 1
}

# --- PHASE 2: STATE LAYER ---
Write-Status "PHASE 2: STATE LAYER (DOCKER)" "Magenta" "🐳"
Set-Location $REPO_ROOT

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

# 1. memOS
Start-ServiceTab "memOS (Hands)" "$REPO_ROOT\memOS" "$PyCmd -m uvicorn omega_kg.memos.main:app --host 0.0.0.0 --port $($Ports.memOS) --reload" "Green"
Start-Sleep -Seconds 2

# 2. OmegaKG
Start-ServiceTab "OmegaKG (Brain)" "$REPO_ROOT\OmegaKG" "$PyCmd -m omega_kg.main --host 0.0.0.0 --port $($Ports.OmegaKG) --reload" "Magenta"
Start-Sleep -Seconds 2

# 3. InGest
Start-ServiceTab "InGest (Stomach)" "$REPO_ROOT\InGest" "$VenvDagster dev -h 0.0.0.0 -p $($Ports.InGest)" "Yellow"

# --- PHASE 4: INTERFACE LAYER ---
if (-not $SkipInterface) {
    Write-Status "PHASE 4: INTERFACE LAYER" "Magenta" "💻"
    Start-ServiceTab "Cortex (Executive)" "$REPO_ROOT\Cortex" "npm run dev -- --port $($Ports.Cortex) --host 0.0.0.0" "Blue"
}

Write-Status "SYSTEM ONLINE" "Green" "⚡"