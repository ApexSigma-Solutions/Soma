# ==============================================================================
# Omega_KG Capture Server Launcher (New Window)
# ==============================================================================
# Starts the capture server in a separate PowerShell window for easy monitoring
# Ensures port alignment and proper configuration
# ==============================================================================

param(
    [string]$Port = "8765",
    [string]$ServerHost = "127.0.0.1",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Omega_KG Capture Server Launcher

Usage:
    .\start-capture-server-window.ps1 [-Port <port>] [-ServerHost <host>]

Parameters:
    -Port         Server port (default: 8765)
    -ServerHost   Server host (default: 127.0.0.1)
    -Help         Show this help message

Examples:
    .\start-capture-server-window.ps1
    .\start-capture-server-window.ps1 -Port 8002
    .\start-capture-server-window.ps1 -ServerHost 0.0.0.0 -Port 8765

"@
    exit 0
}

# ==============================================================================
# Pre-flight Checks
# ==============================================================================

Write-Host "🚀 Omega_KG Capture Server Launcher" -ForegroundColor Cyan
Write-Host "=" * 60

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "   Please copy .env.example to .env and configure it." -ForegroundColor Yellow
    exit 1
}

# Check if Poetry is installed
try {
    $null = poetry --version 2>&1
} catch {
    Write-Host "❌ ERROR: Poetry not found!" -ForegroundColor Red
    Write-Host "   Please install Poetry: https://python-poetry.org/docs/#installation" -ForegroundColor Yellow
    exit 1
}

# Check for conflicting processes
Write-Host "🔍 Checking for existing server processes..." -ForegroundColor Yellow

$existingUvicorn = Get-Process -Name "python" -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -match "uvicorn.*capture_server" }

if ($existingUvicorn) {
    Write-Host "⚠️  WARNING: Existing capture server process detected!" -ForegroundColor Yellow
    Write-Host "   PID: $($existingUvicorn.Id)" -ForegroundColor Yellow
    $response = Read-Host "   Kill existing process? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Stop-Process -Id $existingUvicorn.Id -Force
        Start-Sleep -Seconds 2
        Write-Host "✅ Process terminated" -ForegroundColor Green
    } else {
        Write-Host "❌ Exiting. Please stop the existing process manually." -ForegroundColor Red
        exit 1
    }
}

# Check if port is in use
$portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
    Where-Object { $_.State -eq "Listen" }

if ($portInUse) {
    Write-Host "⚠️  WARNING: Port $Port is already in use!" -ForegroundColor Yellow
    $process = Get-Process -Id $portInUse.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "   Process: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Yellow
    }
    $response = Read-Host "   Continue anyway? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "❌ Exiting." -ForegroundColor Red
        exit 1
    }
}

# ==============================================================================
# Environment Validation
# ==============================================================================

Write-Host "🔧 Validating environment..." -ForegroundColor Yellow

# Read .env file and check critical variables
$envContent = Get-Content ".env" -Raw
$criticalVars = @(
    "NEO4J_PASSWORD",
    "JWT_SECRET_KEY"
)

# Check for EXTENSION_API_KEY (both variants)
$extensionKeyPattern = "EXTENSION_API_KEY(_PRD)?=.+"
if ($envContent -notmatch $extensionKeyPattern) {
    $criticalVars += "EXTENSION_API_KEY"
}

$missingVars = @()
foreach ($var in $criticalVars) {
    if ($envContent -notmatch "$var=.+") {
        $missingVars += $var
    }
}

if ($missingVars.Count -gt 0) {
    Write-Host "⚠️  WARNING: Missing or empty environment variables:" -ForegroundColor Yellow
    foreach ($var in $missingVars) {
        Write-Host "   - $var" -ForegroundColor Yellow
    }
    Write-Host "   The server may fail to start. Check your .env file." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}

# ==============================================================================
# Server Startup
# ==============================================================================

Write-Host ""
Write-Host "✨ Starting Capture Server..." -ForegroundColor Green
Write-Host "   Host: $ServerHost" -ForegroundColor Cyan
Write-Host "   Port: $Port" -ForegroundColor Cyan
Write-Host "   URL:  http://$ServerHost`:$Port" -ForegroundColor Cyan
Write-Host ""

# Set environment variables for this session
$env:APP_HOST = $ServerHost
$env:APP_PORT = $Port

# Build the command to run
$command = "poetry run uvicorn omega_kg.capture_server:app --host $ServerHost --port $Port --log-level info"

# Create a title for the new window
$windowTitle = "Omega_KG Capture Server - Port $Port"

# Start in new window
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& { `
        `$PSHost = Get-Host; `
        `$PSHost.UI.RawUI.WindowTitle = '$windowTitle'; `
        Set-Location '$PWD'; `
        Write-Host ''; `
        Write-Host '╔════════════════════════════════════════════════════════╗' -ForegroundColor Cyan; `
        Write-Host '║     Omega_KG Capture Server - Monitoring Window      ║' -ForegroundColor Cyan; `
        Write-Host '╚════════════════════════════════════════════════════════╝' -ForegroundColor Cyan; `
        Write-Host ''; `
        Write-Host '  Server URL: http://$ServerHost`:$Port' -ForegroundColor Green; `
        Write-Host '  Health:     http://$ServerHost`:$Port/health' -ForegroundColor Green; `
        Write-Host '  Docs:       http://$ServerHost`:$Port/docs' -ForegroundColor Green; `
        Write-Host ''; `
        Write-Host '  Press Ctrl+C to stop the server' -ForegroundColor Yellow; `
        Write-Host '  Close this window to terminate the process' -ForegroundColor Yellow; `
        Write-Host ''; `
        Write-Host '─' * 60 -ForegroundColor Gray; `
        Write-Host ''; `
        $command `
    }"
)

# Wait a moment for the server to start
Start-Sleep -Seconds 3

# ==============================================================================
# Post-Startup Validation
# ==============================================================================

Write-Host "🧪 Testing server health..." -ForegroundColor Yellow

$maxRetries = 5
$retryCount = 0
$healthUrl = "http://$ServerHost`:$Port/health"

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Server is running successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "━" * 60 -ForegroundColor Green
            Write-Host "Server Details:" -ForegroundColor Cyan
            Write-Host "  • Health Check: $healthUrl" -ForegroundColor White
            Write-Host "  • API Docs:     http://$ServerHost`:$Port/docs" -ForegroundColor White
            Write-Host "  • OpenAPI:      http://$ServerHost`:$Port/openapi.json" -ForegroundColor White
            Write-Host ""
            Write-Host "Chrome Extension Configuration:" -ForegroundColor Cyan
            Write-Host "  • Server URL:   http://$ServerHost`:$Port" -ForegroundColor White
            Write-Host "  • Make sure EXTENSION_API_KEY in .env matches your extension" -ForegroundColor Yellow
            Write-Host "━" * 60 -ForegroundColor Green
            Write-Host ""
            Write-Host "✨ Server monitoring window is now open!" -ForegroundColor Green
            Write-Host "   Check the new PowerShell window for server logs." -ForegroundColor Cyan
            exit 0
        }
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "   Waiting for server... (attempt $retryCount/$maxRetries)" -ForegroundColor Gray
            Start-Sleep -Seconds 2
        }
    }
}

Write-Host "⚠️  WARNING: Server started but health check failed" -ForegroundColor Yellow
Write-Host "   The server window is open. Check it for errors." -ForegroundColor Yellow
Write-Host "   Health URL: $healthUrl" -ForegroundColor Gray
exit 0
