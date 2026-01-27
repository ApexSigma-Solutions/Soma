

























































































































DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDs# -----------------------------------------------------------------------------
# Omega_KG Shell Integration - CORRECTED & UNIFIED (ReFS)
# -----------------------------------------------------------------------------
#
# This script integrates the Omega_KG project and OmegaVault session logging
# directly into the PowerShell prompt. It is configured to run from the
# D:\DevDrive (ReFS) for maximum performance.
#

# --- CONFIGURATION (Points to D:\ Dev Drive) ---

# Path to the Obsidian vault for session logging
$env:OMEGA_VAULT = "D:\projects\omegavault.as"

# Directory to store session log files
$env:OMEGA_SESSION_DIR = "$env:OMEGA_VAULT\Sessions"

# Full path to today's session log file
$env:OMEGA_SESSION_LOG = "$env:OMEGA_SESSION_DIR\$(Get-Date -Format yyyy-MM-dd).md"

# Default project root.
# Use Set-OmegaKGEnvironment 'dev' or 'stable' to switch environments dynamically.
$global:OMEGA_KG_PROJECT_ROOT = "D:\projects\Omega_KG_dev"

function Set-OmegaKGEnvironment {
    param(
        [ValidateSet("dev", "stable")]
        [string]$Environment = "dev"
    )
    $global:OMEGA_KG_PROJECT_ROOT = "D:\projects\Omega_KG_$Environment"
    Write-Host "Omega_KG project root set to: $global:OMEGA_KG_PROJECT_ROOT" -ForegroundColor Cyan
    
    # Invalidate the check to force a refresh on next prompt
    $global:OMEGA_KG_CHECK_COMPLETE = $null 
}

# --- HELPER FUNCTIONS ---

function Initialize-OmegaSession {
    <#
    .SYNOPSIS
    Ensures the session log directory and today's log file exist.
    Creates them if they do not.
    #>

    # Create the Sessions directory if it's missing
    if (-not (Test-Path $env:OMEGA_SESSION_DIR)) {
        New-Item -ItemType Directory -Force -Path $env:OMEGA_SESSION_DIR | Out-Null
    }

    # Create today's log file with YAML frontmatter if it's missing
    if (-not (Test-Path $env:OMEGA_SESSION_LOG)) {
        $timestamp = Get-Date -Format "HH:mm:ss"
        $content = @"
---
type: session
date: $(Get-Date -Format yyyy-MM-dd)
start: $timestamp
tags: [session, terminal]
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
    Filters out trivial/noise commands.
    #>
    param(
        [string]$Command,
        [int]$ExitCode = 0,
        [string]$WorkingDirectory = (Get-Location).Path
    )

    # List of trivial commands to ignore (to reduce log noise)
    $trivialCommands = @(
        'ls', 'dir', 'cd', 'pwd', 'echo', 'cls', 'clear', '.', '..',
        'gci', 'cat', 'type', 'gc', 'more', 'help', 'man', 'history', 'h'
    )

    # Try to parse the command to get the base command name
    try {
        $ast = [System.Management.Automation.Language.Parser]::ParseInput($Command, [ref]$null, [ref]$null)
        if ($ast.EndBlock.Statements.Count -gt 0 -and
            $ast.EndBlock.Statements[0].PipelineElements.Count -gt 0 -and
            $ast.EndBlock.Statements[0].PipelineElements[0].CommandElements.Count -gt 0) {
            $commandName = $ast.EndBlock.Statements[0].PipelineElements[0].CommandElements[0].Value
        } else {
            # Fallback for simple commands or parsing errors
            # Trim leading '&', '.', and '\' to handle invocation operators and relative paths
            $commandName = ($Command -split ' ')[0].TrimStart('&', '.', '\')
        }
    } catch {
        # Fallback for simple commands or parsing errors
        # Trim leading '&', '.', and '\' to handle invocation operators and relative paths
        $commandName = ($Command -split ' ')[0].TrimStart('&', '.', '\')
    }

    # Filter out trivial commands
    if ($trivialCommands -contains $commandName) { return }
    if ($Command.Length -lt 3) { return }
    if ($Command -match '^\s*#') { return } # Ignore comments

    $timestamp = Get-Date -Format "HH:mm:ss"
    $statusEmoji = if ($ExitCode -eq 0) { "✅" } else { "❌" }

    # Categorize the command for quick scanning
    $commandType = switch -Regex ($Command) {
        '^git ' { 'git' }
        '^poetry ' { 'poetry' }
        '^docker ' { 'docker' }
        '^python ' { 'python' }
        '^npm ' { 'node' }
        '^cargo ' { 'rust' }
        '^dotnet ' { 'dotnet' }
        '^terraform ' { 'terraform' }
        default { 'shell' }
    }

    $entry = @"

### [$timestamp] $statusEmoji ``$Command``
**Type:** $commandType | **Exit:** $ExitCode | **Path:** ``$WorkingDirectory``

"@

    # Append the formatted entry to the log file
    Add-Content -Path $env:OMEGA_SESSION_LOG -Value $entry
}

function Get-OmegaSessionLog {
    <#
    .SYNOPSIS
    Open today's session log in the default editor (VS Code).
    #>
    if (Test-Path $env:OMEGA_SESSION_LOG) {
        Invoke-Item $env:OMEGA_SESSION_LOG
    } else {
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
    } else {
        Write-Host "Success Rate: N/A" -ForegroundColor Cyan
    }
    Write-Host "Session Log: $env:OMEGA_SESSION_LOG" -ForegroundColor Gray
}

function Add-OmegaGitCommit {
    <#
    .SYNOPSIS
    Appends a Git commit entry to the current Omega session log.
    (This function is intended to be called by other scripts, e.g., a git hook)
    #>
    param(
        [string]$CommitHash,
        [string]$Message
    )

    $entry = @"

#### Git Commit: ``$CommitHash``
``````
$Message
``````

"@
    Add-Content -Path $env:OMEGA_SESSION_LOG -Value $entry
}

# --- SCRIPT INITIALIZATION ---

# Ensure the session log is ready
Initialize-OmegaSession

# Source the venv helper functions (activate-omega, etc.)
# This path *must* exist for the 'activate-omega' command to work.
$venvScriptPath = Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts\omega-venv.ps1"
if (Test-Path $venvScriptPath) {
    . $venvScriptPath
} else {
    Write-Host "[!] WARNING: venv script not found at '$venvScriptPath'. 'activate-omega' will fail." -ForegroundColor Yellow
}

# Print the welcome message once per session
if (-not $global:OMEGA_KG_WELCOME_PRINTED) {
    Write-Host "✨ Omega_KG shell integration loaded (ReFS)" -ForegroundColor Green
    Write-Host "   Vault: $env:OMEGA_VAULT" -ForegroundColor Gray
    Write-Host "   Session: $env:OMEGA_SESSION_LOG" -ForegroundColor Gray
    Write-Host "   Project Root: $global:OMEGA_KG_PROJECT_ROOT" -ForegroundColor Gray
    $global:OMEGA_KG_WELCOME_PRINTED = $true
}

# -----------------------------------------------------------------------------
# OMEGA_KG PROJECT HOOK
#
# This function is called by prompt() to run pre-flight checks *once*
# per session when entering the project directory.
# -----------------------------------------------------------------------------

function Global:Check-OmegaKG-Environment {
    try {
        # Check 1: Are we in the project directory?
        if ($global:OMEGA_KG_PROJECT_ROOT -and (Get-Location).Path -like "$global:OMEGA_KG_PROJECT_ROOT*") {
            
            # Check 2: Have we already run the checks in this terminal session?
            if (-not (Test-Path "variable:global:OMEGA_KG_CHECK_COMPLETE")) {
                
                # --- RUN ONCE ---
                
                # 1. Run your existing activation (prints status, loads venv, etc.)
                if (Get-Command activate-omega -ErrorAction SilentlyContinue) {
                    activate-omega
                } else {
                    Write-Host "[X] FAILURE: 'activate-omega' function not found. (Sourcing 'omega-venv.ps1' failed)" -ForegroundColor Red
                }
                
                # 2. SKIP pre-flight checks on shell startup to prevent hangs
                #    Run 'omega-preflight' manually if needed
                # $checkScript = Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"
                # if (Test-Path $checkScript) {
                #     & $checkScript
                # }
                
                # 3. Set the global "gate" to 'true' so this doesn't run again
                $global:OMEGA_KG_CHECK_COMPLETE = $true
            }
        }
    } catch {
        # Catch any errors from the check script
        Write-Host "An error occurred during environment checks: $_" -ForegroundColor Red
    }
}

function omega-preflight {
    <#
    .SYNOPSIS
    Run Omega_KG pre-flight checks manually (Docker, dependencies, etc.)
    #>
    if (-not $global:OMEGA_KG_PROJECT_ROOT) {
        Write-Error "Not in an Omega_KG environment. Use 'omega-dev' or 'omega-stable' first."
        return
    }
    $checkScript = Join-Path (Join-Path $global:OMEGA_KG_PROJECT_ROOT "scripts") "Start-OmegaKGDev.ps1"
    if (Test-Path $checkScript) {
        & $checkScript
    } else {
        Write-Host "[!] WARNING: 'Start-OmegaKGDev.ps1' not found." -ForegroundColor Yellow
    }
}

# -----------------------------------------------------------------------------
# UNIFIED PROMPT FUNCTION
#
# This single function runs on every prompt to:
# 1. Reset the pre-flight check if we leave the project.
# 2. Run the pre-flight check if we enter the project.
# 3. Log the previous command.
# 4. Display the prompt string.
# -----------------------------------------------------------------------------

function prompt {
    
    # 1. Reset the check if we leave the project directory
    $currentPath = (Get-Location).Path
    if ($global:OMEGA_KG_PROJECT_ROOT -and $global:OMEGA_KG_CHECK_COMPLETE -and ($currentPath -notlike "$global:OMEGA_KG_PROJECT_ROOT*")) {
        $global:OMEGA_KG_CHECK_COMPLETE = $null
        Write-Host "Exited Omega_KG project. Pre-flight checks will run on next entry." -ForegroundColor Cyan
    }

    # 2. Run our environment checker
    Global:Check-OmegaKG-Environment
    
    # 3. Command logging and session integration
    # Get the last command from history
    $history = Get-History -Count 1 -ErrorAction SilentlyContinue
    if ($history -and $history.ExecutionStatus -eq 'Completed') {
        
        # Check the last several lines of the log to prevent duplicates (e.g., holding Enter)
        $lastLoggedLines = Get-Content $env:OMEGA_SESSION_LOG -Tail 10 -ErrorAction SilentlyContinue
        if ($lastLoggedLines -notmatch [regex]::Escape($history.CommandLine)) {
            $exitCode = if ($null -ne $history.ExitCode) { $history.ExitCode } elseif ($LASTEXITCODE -ne $null) { $LASTEXITCODE } elseif ($?) { 0 } else { 1 }
            Add-OmegaCommand -Command $history.CommandLine -ExitCode $exitCode -WorkingDirectory (Get-Location).Path
        }
    }

    # 4. Return the enhanced prompt string with venv and project context
    $venv = $env:VIRTUAL_ENV
    $venvName = if ($venv) { "($(Split-Path $venv -Leaf)) " } else { "" }
    $projectName = if ($global:OMEGA_KG_PROJECT_ROOT) { "[$([System.IO.Path]::GetFileName($global:OMEGA_KG_PROJECT_ROOT))] " } else { "" }
    "PS $projectName$venvName$($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}


# --- OMEGA_KG COMMAND SHORTCUTS ---
# Quick environment switching and server management commands

function omega-dev {
    <#
    .SYNOPSIS
    Switch to the dev environment
    #>
    Set-OmegaKGEnvironment -Environment dev
}

function omega-stable {
    <#
    .SYNOPSIS
    Switch to the stable environment
    #>
    Set-OmegaKGEnvironment -Environment stable
}

function omega-start {
    <#
    .SYNOPSIS
    Start the Omega_KG server in foreground mode
    #>
    if (-not $global:OMEGA_KG_PROJECT_ROOT) {
        Write-Error "Not in an Omega_KG environment. Use 'omega-dev' or 'omega-stable' first."
        return
    }
    & "$global:OMEGA_KG_PROJECT_ROOT\scripts\Start-OmegaServer.ps1" -Mode foreground
}

function omega-start-term {
    <#
    .SYNOPSIS
    Start the Omega_KG server in a new terminal window
    #>
    if (-not $global:OMEGA_KG_PROJECT_ROOT) {
        Write-Error "Not in an Omega_KG environment. Use 'omega-dev' or 'omega-stable' first."
        return
    }
    & "$global:OMEGA_KG_PROJECT_ROOT\scripts\Start-OmegaServer.ps1" -Mode terminal
}

function omega-start-bg {
    <#
    .SYNOPSIS
    Start the Omega_KG server in background mode
    #>
    if (-not $global:OMEGA_KG_PROJECT_ROOT) {
        Write-Error "Not in an Omega_KG environment. Use 'omega-dev' or 'omega-stable' first."
        return
    }
    & "$global:OMEGA_KG_PROJECT_ROOT\scripts\Start-OmegaServer.ps1" -Mode background
}

function omega-stop {
    <#
    .SYNOPSIS
    Stop the running Omega_KG server
    #>
    if (-not $global:OMEGA_KG_PROJECT_ROOT) {
        Write-Error "Not in an Omega_KG environment. Use 'omega-dev' or 'omega-stable' first."
        return
    }
    & "$global:OMEGA_KG_PROJECT_ROOT\scripts\Start-OmegaServer.ps1" -Mode stop
}

function omega-restart {
    <#
    .SYNOPSIS
    Restart the Omega_KG server
    #>
    if (-not $global:OMEGA_KG_PROJECT_ROOT) {
        Write-Error "Not in an Omega_KG environment. Use 'omega-dev' or 'omega-stable' first."
        return
    }
    & "$global:OMEGA_KG_PROJECT_ROOT\scripts\Start-OmegaServer.ps1" -Mode restart
}

function omega-status {
    <#
    .SYNOPSIS
    Display the status of the Omega_KG server
    #>
    if (-not $global:OMEGA_KG_PROJECT_ROOT) {
        Write-Error "Not in an Omega_KG environment. Use 'omega-dev' or 'omega-stable' first."
        return
    }
    & "$global:OMEGA_KG_PROJECT_ROOT\scripts\Start-OmegaServer.ps1" -Mode status
}

function omega-code {
    <#
    .SYNOPSIS
    Open the Omega_KG project in VS Code
    
    .PARAMETER Environment
    Which environment to open: 'dev' or 'stable' (default: 'dev')
    #>
    param([string]$Environment = "dev")
    $projectPath = if ($Environment -eq "stable") {
        "d:\projects\Omega_KG_stable"
    } else {
        "d:\projects\Omega_KG_dev"
    }
    & code $projectPath
}

# --- END OMEGA_KG SHORTCUTS ---
# --- END OF PROFILE ---
