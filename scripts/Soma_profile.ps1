# -----------------------------------------------------------------------------
# Soma Ecosystem Shell Integration
# -----------------------------------------------------------------------------
#
# This script integrates the Soma biomorphic knowledge ecosystem with PowerShell.
# Session logging to OmegaVault is retained for command history tracking.
#
# Updated: 2026-02-05 - Refactored for Soma monorepo architecture
#

# --- CONFIGURATION ---

# Path to the Obsidian vault for session logging
$env:OMEGA_VAULT = "D:\projects\Soma\OmegaVault"

# Directory to store session log files
$env:OMEGA_SESSION_DIR = "$env:OMEGA_VAULT\Sessions"

# Full path to today's session log file
$env:OMEGA_SESSION_LOG = "$env:OMEGA_SESSION_DIR\$(Get-Date -Format yyyy-MM-dd).md"

# Soma ecosystem root directory
$global:SOMA_ROOT = "D:\projects\Soma"

# --- HELPER FUNCTIONS ---

function Initialize-OmegaSession {
    <#
    .SYNOPSIS
    Ensures the session log directory and today's log file exist.
    #>

    if (-not (Test-Path $env:OMEGA_SESSION_DIR)) {
        New-Item -ItemType Directory -Force -Path $env:OMEGA_SESSION_DIR | Out-Null
    }

    if (-not (Test-Path $env:OMEGA_SESSION_LOG)) {
        $timestamp = Get-Date -Format "HH:mm:ss"
        $content = @"
---
type: session
date: $(Get-Date -Format yyyy-MM-dd)
start: $timestamp
tags: [session, terminal, soma]
---

# Terminal Session $(Get-Date -Format yyyy-MM-dd)

Started: $timestamp

## Commands

"@
        Set-Content -Path $env:OMEGA_SESSION_LOG -Value $content
    }
}

function Add-OmegaCommand {
    <#
    .SYNOPSIS
    Appends the last executed command to the session log.
    #>
    param(
        [string]$Command,
        [int]$ExitCode = 0,
        [string]$WorkingDirectory = (Get-Location).Path
    )

    # List of trivial commands to ignore
    $trivialCommands = @(
        'ls', 'dir', 'cd', 'pwd', 'echo', 'cls', 'clear', '.', '..',
        'gci', 'cat', 'type', 'gc', 'more', 'help', 'man', 'history', 'h'
    )

    try {
        $ast = [System.Management.Automation.Language.Parser]::ParseInput($Command, [ref]$null, [ref]$null)
        if ($ast.EndBlock.Statements.Count -gt 0 -and
            $ast.EndBlock.Statements[0].PipelineElements.Count -gt 0 -and
            $ast.EndBlock.Statements[0].PipelineElements[0].CommandElements.Count -gt 0) {
            $commandName = $ast.EndBlock.Statements[0].PipelineElements[0].CommandElements[0].Value
        }
        else {
            $commandName = ($Command -split ' ')[0].TrimStart('&', '.', '\')
        }
    }
    catch {
        $commandName = ($Command -split ' ')[0].TrimStart('&', '.', '\')
    }

    if ($trivialCommands -contains $commandName) { return }
    if ($Command.Length -lt 3) { return }
    if ($Command -match '^\s*#') { return }

    $timestamp = Get-Date -Format "HH:mm:ss"
    $statusEmoji = if ($ExitCode -eq 0) { "✅" } else { "❌" }

    $commandType = switch -Regex ($Command) {
        '^git ' { 'git' }
        '^poetry ' { 'poetry' }
        '^docker ' { 'docker' }
        '^python ' { 'python' }
        '^npm ' { 'node' }
        default { 'shell' }
    }

    $entry = @"

### [$timestamp] $statusEmoji ``$Command``
**Type:** $commandType | **Exit:** $ExitCode | **Path:** ``$WorkingDirectory``

"@

    Add-Content -Path $env:OMEGA_SESSION_LOG -Value $entry
}

function Get-OmegaSessionLog {
    <#
    .SYNOPSIS
    Open today's session log in the default editor.
    #>
    if (Test-Path $env:OMEGA_SESSION_LOG) {
        Invoke-Item $env:OMEGA_SESSION_LOG
    }
    else {
        Write-Host "No session log for today" -ForegroundColor Yellow
    }
}

function Get-OmegaStats {
    <#
    .SYNOPSIS
    Show session statistics for today.
    #>
    if (-not (Test-Path $env:OMEGA_SESSION_LOG)) {
        Write-Host "No session log for today" -ForegroundColor Yellow
        return
    }

    $content = Get-Content $env:OMEGA_SESSION_LOG -Raw
    $commands = ([regex]::Matches($content, '###')).Count
    $errors = ([regex]::Matches($content, '❌')).Count
    $success = $commands - $errors

    Write-Host "Total Commands: $commands" -ForegroundColor White
    Write-Host "Success: $success" -ForegroundColor Green
    Write-Host "Errors: $errors" -ForegroundColor Red
    if ($commands -gt 0) {
        Write-Host "Success Rate: $([math]::Round(($success/$commands)*100))%" -ForegroundColor Cyan
    }
}

# --- SCRIPT INITIALIZATION ---

Initialize-OmegaSession

# Print welcome message once per session
if (-not $global:SOMA_WELCOME_PRINTED) {
    Write-Host "🧠 Soma Ecosystem Shell Integration" -ForegroundColor Green
    Write-Host "   Vault: $env:OMEGA_VAULT" -ForegroundColor Gray
    Write-Host "   Session: $env:OMEGA_SESSION_LOG" -ForegroundColor Gray
    Write-Host "   Soma Root: $global:SOMA_ROOT" -ForegroundColor Gray
    $global:SOMA_WELCOME_PRINTED = $true
}

# -----------------------------------------------------------------------------
# PROMPT FUNCTION
# -----------------------------------------------------------------------------

function prompt {
    # Command logging
    $history = Get-History -Count 1 -ErrorAction SilentlyContinue
    if ($history -and $history.ExecutionStatus -eq 'Completed') {
        $lastLoggedLines = Get-Content $env:OMEGA_SESSION_LOG -Tail 10 -ErrorAction SilentlyContinue
        if ($lastLoggedLines -notmatch [regex]::Escape($history.CommandLine)) {
            $exitCode = if ($null -ne $history.ExitCode) { $history.ExitCode } elseif ($null -ne $LASTEXITCODE) { $LASTEXITCODE } elseif ($?) { 0 } else { 1 }
            Add-OmegaCommand -Command $history.CommandLine -ExitCode $exitCode -WorkingDirectory (Get-Location).Path
        }
    }

    # Enhanced prompt with venv context
    $venv = $env:VIRTUAL_ENV
    $venvName = if ($venv) { "($(Split-Path $venv -Leaf)) " } else { "" }
    
    # Show Soma context if in Soma directory
    $currentPath = (Get-Location).Path
    $somaContext = if ($currentPath -like "$global:SOMA_ROOT*") { "[Soma] " } else { "" }
    
    "PS $somaContext$venvName$($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}

# -----------------------------------------------------------------------------
# SOMA ECOSYSTEM SHORTCUTS
# -----------------------------------------------------------------------------

function soma {
    <#
    .SYNOPSIS
    Navigate to the Soma ecosystem root directory.
    #>
    Set-Location $global:SOMA_ROOT
}

function soma-start {
    <#
    .SYNOPSIS
    Start the Soma ecosystem using start_ecosystem.ps1
    #>
    param(
        [switch]$ShowConsole,
        [switch]$SkipMigrations,
        [switch]$Persistent
    )
    
    Push-Location $global:SOMA_ROOT
    $params = @()
    if ($ShowConsole) { $params += "-ShowConsole" }
    if ($SkipMigrations) { $params += "-SkipMigrations" }
    if ($Persistent) { $params += "-Persistent" }
    
    & "$global:SOMA_ROOT\start_ecosystem.ps1" @params
    Pop-Location
}

function soma-stop {
    <#
    .SYNOPSIS
    Stop Docker containers for Soma infrastructure.
    #>
    Push-Location $global:SOMA_ROOT
    docker compose down
    Pop-Location
}

function soma-logs {
    <#
    .SYNOPSIS
    Show recent ecosystem logs.
    #>
    param([string]$Service = "")
    
    $logsDir = "$global:SOMA_ROOT\logs"
    if ($Service) {
        $logFile = Get-ChildItem "$logsDir\$Service*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($logFile) {
            Get-Content $logFile.FullName -Tail 50
        }
        else {
            Write-Host "No logs found for service: $Service" -ForegroundColor Yellow
        }
    }
    else {
        $latestLog = Get-ChildItem "$logsDir\startup_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestLog) {
            Get-Content $latestLog.FullName -Tail 50
        }
    }
}

function soma-status {
    <#
    .SYNOPSIS
    Check status of Soma services.
    #>
    Write-Host "`n🧠 Soma Ecosystem Status" -ForegroundColor Cyan
    Write-Host "=" * 40 -ForegroundColor DarkGray
    
    $services = @(
        @{ Name = "Postgres"; Port = 5432 },
        @{ Name = "Neo4j"; Port = 7687 },
        @{ Name = "Redis"; Port = 6380 },
        @{ Name = "InGress"; Port = 8000 },
        @{ Name = "InGest"; Port = 8766 },
        @{ Name = "OmegaKG"; Port = 8765 },
        @{ Name = "memOS"; Port = 8768 },
        @{ Name = "Cortex"; Port = 6001 }
    )
    
    foreach ($svc in $services) {
        $connected = Test-NetConnection -ComputerName localhost -Port $svc.Port -WarningAction SilentlyContinue -InformationLevel Quiet
        $status = if ($connected) { "✅ Online" } else { "❌ Offline" }
        Write-Host "  $($svc.Name.PadRight(12)) :$($svc.Port)  $status"
    }
    Write-Host ""
}

function soma-code {
    <#
    .SYNOPSIS
    Open Soma project in VS Code.
    #>
    code $global:SOMA_ROOT
}

# --- END SOMA SHORTCUTS ---
# --- END OF PROFILE ---
