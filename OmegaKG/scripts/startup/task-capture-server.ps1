# Omega_KG Capture Server — Active App Monitor
# Starts capture-server in background when a supported AI web app is active
# Stops server when all supported apps are closed

# Supported AI sites that trigger capture server
$SupportedApps = @(
    "gemini.google.com",
    "chat.openai.com",
    "claude.ai",
    "perplexity.ai",
    "github.com/copilot",
    "chat.qwen.ai",
    "copilot.microsoft.com",
    "copilot.com"
)

# Configuration
$ProjectPath = "$env:USERPROFILE\OneDrive\ApexSigma\Omega_KG"
$CheckIntervalSeconds = 5  # Check every 5 seconds if apps are active
$ServerLogFile = "$ProjectPath\capture-server.log"

function Get-ActiveBrowserURLs {
    <#
    .SYNOPSIS
    Gets URLs from active browser windows (Chrome, Edge, Firefox)
    #>
    try {
        $urls = @()

        # Chrome/Edge via UIAutomation (accessible from PowerShell)
        try {
            $chrome = Get-Process chrome -ErrorAction SilentlyContinue
            if ($chrome) {
                # Try to get window titles which sometimes contain URLs
                $chrome | ForEach-Object {
                    if ($_.MainWindowTitle) {
                        $urls += $_.MainWindowTitle
                    }
                }
            }
        } catch {}

        # Edge
        try {
            $edge = Get-Process msedge -ErrorAction SilentlyContinue
            if ($edge) {
                $edge | ForEach-Object {
                    if ($_.MainWindowTitle) {
                        $urls += $_.MainWindowTitle
                    }
                }
            }
        } catch {}

        # Firefox
        try {
            $firefox = Get-Process firefox -ErrorAction SilentlyContinue
            if ($firefox) {
                $firefox | ForEach-Object {
                    if ($_.MainWindowTitle) {
                        $urls += $_.MainWindowTitle
                    }
                }
            }
        } catch {}

        return $urls
    } catch {
        Write-Warning "Error detecting browser URLs: $_"
        return @()
    }
}

function Test-SupportedAppActive {
    <#
    .SYNOPSIS
    Checks if any supported AI app is currently active in a browser
    #>
    $activeURLs = Get-ActiveBrowserURLs

    foreach ($url in $activeURLs) {
        foreach ($app in $SupportedApps) {
            if ($url -match [regex]::Escape($app)) {
                return $true
            }
        }
    }

    return $false
}

function Start-CaptureServer {
    <#
    .SYNOPSIS
    Starts capture-server in background if not already running
    #>
    $existingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "capture.server|capture_server" }

    if ($existingProcess) {
        Write-Host "$(Get-Date -Format 'HH:mm:ss') ℹ️  Capture server already running (PID: $($existingProcess.Id))"
        return $true
    }

    try {
        Write-Host "$(Get-Date -Format 'HH:mm:ss') 🚀 Starting capture server..."

        # Start server in background
        $process = Start-Process -FilePath "powershell.exe" `
            -ArgumentList "-NoProfile -WindowStyle Hidden -Command `"cd '$ProjectPath'; poetry run capture-server`"" `
            -PassThru `
            -ErrorAction Stop

        Write-Host "$(Get-Date -Format 'HH:mm:ss') ✅ Capture server started (PID: $($process.Id))"
        return $true
    } catch {
        Write-Host "$(Get-Date -Format 'HH:mm:ss') ❌ Failed to start capture server: $_" -ForegroundColor Red
        return $false
    }
}

function Stop-CaptureServer {
    <#
    .SYNOPSIS
    Stops the running capture-server process
    #>
    try {
        $processes = Get-Process -Name "python" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match "capture.server|capture_server" }

        if ($processes) {
            $processes | ForEach-Object {
                Write-Host "$(Get-Date -Format 'HH:mm:ss') ⛔ Stopping capture server (PID: $($_.Id))..."
                Stop-Process -InputObject $_ -Force -ErrorAction SilentlyContinue
            }
            Write-Host "$(Get-Date -Format 'HH:mm:ss') ✅ Capture server stopped"
        }
    } catch {
        Write-Host "$(Get-Date -Format 'HH:mm:ss') ⚠️  Error stopping capture server: $_" -ForegroundColor Yellow
    }
}

function Write-Header {
    param([string]$Message)
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
}

# Main monitoring loop
Write-Header "Omega_KG Capture Server — App Monitor"
Write-Host "Checking for active AI web apps every $CheckIntervalSeconds seconds"
Write-Host "Supported apps: $($SupportedApps -join ', ')`n"

$serverRunning = $false

try {
    while ($true) {
        $appActive = Test-SupportedAppActive

        if ($appActive -and -not $serverRunning) {
            # App became active, start server
            if (Start-CaptureServer) {
                $serverRunning = $true
            }
        } elseif (-not $appActive -and $serverRunning) {
            # App became inactive, stop server
            Stop-CaptureServer
            $serverRunning = $false
        } else {
            # Status unchanged
            $status = if ($appActive) { "✓ Active app detected" } else { "○ No active app" }
            $serverStatus = if ($serverRunning) { "(Server running)" } else { "(Server idle)" }
            Write-Host "$(Get-Date -Format 'HH:mm:ss') $status $serverStatus" -ForegroundColor Gray
        }

        Start-Sleep -Seconds $CheckIntervalSeconds
    }
} catch {
    Write-Host "`n❌ Monitor error: $_" -ForegroundColor Red
    Stop-CaptureServer
    exit 1
}
