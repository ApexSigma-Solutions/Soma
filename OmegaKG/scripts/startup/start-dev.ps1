# --- START: .env LOADER ---
# (The .env loader code is here... no changes from the previous version)
# Get the directory where the script itself is located
$ScriptDir = $PSScriptRoot

# Assume the project root is one level up from the 'scripts' directory
$ProjectRoot = (Get-Item $ScriptDir).Parent.FullName
$EnvFile = Join-Path $ProjectRoot ".env"

if (Test-Path $EnvFile) {
    Write-Host "Found .env file. Loading environment variables..."
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        # Skip empty lines and comments
        if ($line -and $line -notmatch '^\s*#') {
            $parts = $line.Split('=', 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()

                # Remove surrounding quotes (single or double) from the value
                $value = $value -replace '^"|"$' -replace "^'|'$"

                # Set the environment variable for this script's session
                [Environment]::SetEnvironmentVariable($key, $value, 'Process')
            }
        }
    }
} else {
    Write-Warning "!!! .env file not found at '$EnvFile'. Script will use defaults. !!!"
}
# --- END: .env LOADER ---

# -----------------------------------------------------------------------------
# Omega_KG Development Environment Pre-Flight Check (v1.2)
#
# v1.2: Fixed hotkey conflict (N vs E) and integrated with
#       'start-capture-server.ps1' to prevent duplicate process.
# -----------------------------------------------------------------------------

# --- UTILITY FUNCTIONS ---
# (Functions: Write-Check, Write-Success, Write-Failure, etc. are here... no changes)
function Write-Check {
    param([string]$Message)
    Write-Host "Checking: $Message" -ForegroundColor Cyan
}
function Write-Success {
    param([string]$Message)
    Write-Host "  [✓] SUCCESS: $Message" -ForegroundColor Green
}
function Write-Failure {
    param([string]$Message)
    Write-Host "  [X] FAILURE: $Message" -ForegroundColor Red
    $global:allChecksPassed = $false
}
function Write-Warning {
    param([string]$Message)
    Write-Host "  [!] WARNING: $Message" -ForegroundColor Yellow
}
function Write-Info {
    param([string]$Message)
    Write-Host "  [i] INFO: $Message" -ForegroundColor Gray
}

# --- SCRIPT START ---
Write-Host "--- OMEGA_KG PRE-FLIGHT CHECKS ---" -ForegroundColor Yellow
$global:allChecksPassed = $true

# ---------------------------------
# 1. NEO4J DOCKER CHECKS
# ---------------------------------
# (... No changes to this section. It worked perfectly.)
Write-Check "Neo4j Docker container (from .env)..."
$containerName = if ($env:NEO4J_CONTAINER_NAME) { $env:NEO4J_CONTAINER_NAME } else { "neo4j-db-stable" }
$neo4jNetwork = if ($env:NEO4J_DOCKER_NETWORK) { $env:NEO4J_DOCKER_NETWORK } else { "omega_kg_stable_default" }
$neo4jBoltPort = if ($env:NEO4J_PORT) { $env:NEO4J_PORT } else { 7687 }
$neo4jUser = if ($env:NEO4J_USER) { $env:NEO4J_USER } else { "neo4j" }
$neo4jPassword = $env:NEO4J_PASSWORD
Write-Info "  Target: $containerName on $neo4jNetwork"
$containerID = docker ps -q -f "name=$containerName" -f "status=running"
if (-not $containerID) {
    Write-Failure "Container '$containerName' is not running. (Try: docker start $containerName)"
} else {
    Write-Success "Container '$containerName' is running (ID: $($containerID.Substring(0,12)))."
    $networkCheck = docker inspect $containerID -f '{{.NetworkSettings.Networks}}'
    if ($networkCheck -notlike "*$neo4jNetwork*") {
        Write-Failure "Container is not attached to the '$neo4jNetwork' network."
    } else {
        Write-Success "Container is on the '$neo4jNetwork' network."
    }
    $portMapping = docker port $containerID "$neo4jBoltPort/tcp"
    if (-not $portMapping) {
        Write-Failure "Neo4j Bolt port ($neo4jBoltPort) is not mapped. (Check 'docker ps' port bindings)"
    } else {
        Write-Success "Neo4j Bolt port ($neo4jBoltPort) is mapped."
    }
    $health = docker inspect $containerID -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}'
    switch ($health) {
        "healthy" { Write-Success "Neo4j container is healthy." }
        "unhealthy" { Write-Failure "Neo4j container is running but 'unhealthy'." }
        "starting" { Write-Warning "Neo4j container is still 'starting'." }
        "not-configured" {
            if (-not $neo4jPassword) {
                Write-Warning "Container does not have a health check. Cannot suggest one as NEO4J_PASSWORD is not in .env."
            } else {
                Write-Warning "Container does not have a health check. To add one, update your docker-compose.yml:
                healthcheck:
                  test: ['CMD', 'cypher-shell', '-u', '$neo4jUser', '-p', '$neo4jPassword', 'RETURN 1']
                  interval: 30s
                  timeout: 10s
                  retries: 5"
            }
        }
    }
}

# ---------------------------------
# 2. POETRY ENVIRONMENT CHECKS
# ---------------------------------
# (... No changes to this section.)
Write-Check "Poetry virtual environment..."
if (-not $env:VIRTUAL_ENV) {
    Write-Failure "'.venv' is not active. This script should be run *after* sourcing 'activate-omega'."
} else {
    Write-Success "'.venv' is active: $env:VIRTUAL_ENV"
}
Write-Check "Poetry dependencies..."
$syncOutput = ""
$syncError = ""
$syncProcess = Start-Process poetry -ArgumentList "install", "--dry-run", "--no-root" -NoNewWindow -RedirectStandardOutput "sync_stdout.txt" -RedirectStandardError "sync_stderr.txt" -Wait -PassThru
$syncOutput = Get-Content "sync_stdout.txt" -Raw
$syncError = Get-Content "sync_stderr.txt" -Raw
Remove-Item "sync_stdout.txt","sync_stderr.txt" -ErrorAction SilentlyContinue
if ($syncProcess.ExitCode -ne 0) {
    if ($syncOutput -like "*Dependencies are locked*") {
        Write-Warning "Dependencies are out of sync. Running 'poetry install'..."
        poetry install --no-root | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Success "Dependencies synced." }
        else { Write-Failure "Failed to sync dependencies. Run 'poetry install' manually." }
    } else { Write-Failure "'poetry install --dry-run' failed. Error output:`n$syncError" }
} else { Write-Success "Dependencies are in sync." }

# ---------------------------------
# 3. SHELL INTEGRATION CHECK
# ---------------------------------
# (... No changes to this section.)
Write-Check "Shell integration..."
if (-not (Get-Command activate-omega -ErrorAction SilentlyContinue)) {
    Write-Warning "The 'activate-omega' function itself was not found. Shell integration may be broken."
} else {
    Write-Success "'activate-omega' function is loaded."
}
@( "pytest", "pytest-cov", "pydantic", "pre-commit" ) | ForEach-Object {
    poetry show $_ --no-interaction > $null 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Failure "$_ is not installed in the venv." }
}
Write-Success "Core Python tooling (pytest, pytest-cov, pydantic, pre-commit) is installed."
$trunkCheck = Get-Command trunk -ErrorAction SilentlyContinue
if (-not $trunkCheck) { Write-Failure "Trunk.io binary is not available in your PATH." }
else { Write-Success "Trunk.io binary is available." }


# ---------------------------------
# FINAL DECISION BLOCK
# ---------------------------------
if ($global:allChecksPassed) {
    Write-Host ""
    Write-Host "--- ALL PRE-FLIGHT CHECKS PASSED ---" -ForegroundColor Green
    Write-Host ""

    # ---------------------------------
    # 5. SERVER START-UP
    # ---------------------------------

    $serverHost = if ($env:CAPTURE_SERVER_HOST) { $env:CAPTURE_SERVER_HOST } else { "127.0.0.1" }
    $serverPort = if ($env:CAPTURE_SERVER_PORT) { $env:CAPTURE_SERVER_PORT } else { 8765 }
    $serverModule = if ($env:CAPTURE_SERVER_MODULE) { $env:CAPTURE_SERVER_MODULE } else { "omega_kg.capture_server:app" }

    $title = "Omega_KG Server"
    $message = "All checks passed. Start the FastAPI server ($serverModule) on $serverHost`:$serverPort?"

    # --- FIX 1: Unambiguous hotkeys ---
    $newWindow = [System.Management.Automation.Host.ChoiceDescription]::new("&New Window", "Start uvicorn in a new, separate terminal window.")
    $thisTerminal = [System.Management.Automation.Host.ChoiceDescription]::new("&This Terminal", "Start uvicorn in this terminal (blocks prompt).")
    $exitChoice = [System.Management.Automation.Host.ChoiceDescription]::new("&Exit (Do not start)", "Do not start the server.")
    $options = [System.Management.Automation.Host.ChoiceDescription[]]($newWindow, $thisTerminal, $exitChoice)
    $default = 0 # Default to New Window

    $result = $host.ui.PromptForChoice($title, $message, $options, $default)

    # --- FIX 2: Call the script that has the "is running" check ---
    $startScriptPath = Join-Path $PSScriptRoot "start-capture-server.ps1"

    switch ($result) {
        0 {
            Write-Info "Starting server in new window (via start-capture-server.ps1)..."
            # This script already starts in a new job, so just call it.
            & $startScriptPath
        }
        1 {
            Write-Info "Starting server in this terminal. (Press Ctrl+C to stop)"

            # We must *manually* check if it's running, since we aren't using the other script
            $existing = Get-CimInstance Win32_Process -Filter "Name = 'uvicorn.exe'" |
                Where-Object { $_.CommandLine -match "omega_kg.capture_server" }

            if ($existing) {
                Write-Warning "⚠ Capture server already running (PID: $($existing.Id))"
            }
        }
        2 {
            Write-Info "Server not started."
        }
    }
} else {
    Write-Host ""
    Write-Host "--- PRE-FLIGHT CHECKS FAILED ---" -ForegroundColor Red
    Write-Host "Server start-up aborted. Please fix the errors above." -ForegroundColor Red
}
# --- END: .env LOADER ---

# -----------------------------------------------------------------------------
# Omega_KG Development Environment Pre-Flight Check (v1.2)
#
# v1.2: Fixed hotkey conflict (N vs E) and integrated with
#       'start-capture-server.ps1' to prevent duplicate process.
# -----------------------------------------------------------------------------

# --- UTILITY FUNCTIONS ---
# (Functions: Write-Check, Write-Success, Write-Failure, etc. are here... no changes)
function Write-Check {
    param([string]$Message)
    Write-Host "Checking: $Message" -ForegroundColor Cyan
}
function Write-Success {
    param([string]$Message)
    Write-Host "  [✓] SUCCESS: $Message" -ForegroundColor Green
}
function Write-Failure {
    param([string]$Message)
    Write-Host "  [X] FAILURE: $Message" -ForegroundColor Red
    $global:allChecksPassed = $false
}
function Write-Warning {
    param([string]$Message)
    Write-Host "  [!] WARNING: $Message" -ForegroundColor Yellow
}
function Write-Info {
    param([string]$Message)
    Write-Host "  [i] INFO: $Message" -ForegroundColor Gray
}

# --- SCRIPT START ---
Write-Host "--- OMEGA_KG PRE-FLIGHT CHECKS ---" -ForegroundColor Yellow
$global:allChecksPassed = $true

# ---------------------------------
# 1. NEO4J DOCKER CHECKS
# ---------------------------------
# (... No changes to this section. It worked perfectly.)
Write-Check "Neo4j Docker container (from .env)..."
$containerName = if ($env:NEO4J_CONTAINER_NAME) { $env:NEO4J_CONTAINER_NAME } else { "neo4j-db-stable" }
$neo4jNetwork = if ($env:NEO4J_DOCKER_NETWORK) { $env:NEO4J_DOCKER_NETWORK } else { "omega_kg_stable_default" }
$neo4jBoltPort = if ($env:NEO4J_PORT) { $env:NEO4J_PORT } else { 7687 }
$neo4jUser = if ($env:NEO4J_USER) { $env:NEO4J_USER } else { "neo4j" }
$neo4jPassword = $env:NEO4J_PASSWORD
Write-Info "  Target: $containerName on $neo4jNetwork"
$containerID = docker ps -q -f "name=$containerName" -f "status=running"
if (-not $containerID) {
    Write-Failure "Container '$containerName' is not running. (Try: docker start $containerName)"
} else {
    Write-Success "Container '$containerName' is running (ID: $($containerID.Substring(0,12)))."
    $networkCheck = docker inspect $containerID -f '{{.NetworkSettings.Networks}}'
    if ($networkCheck -notlike "*$neo4jNetwork*") {
        Write-Failure "Container is not attached to the '$neo4jNetwork' network."
    } else {
        Write-Success "Container is on the '$neo4jNetwork' network."
    }
    $portMapping = docker port $containerID "$neo4jBoltPort/tcp"
    if (-not $portMapping) {
        Write-Failure "Neo4j Bolt port ($neo4jBoltPort) is not mapped. (Check 'docker ps' port bindings)"
    } else {
        Write-Success "Neo4j Bolt port ($neo4jBoltPort) is mapped."
    }
    $health = docker inspect $containerID -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}'
    switch ($health) {
        "healthy" { Write-Success "Neo4j container is healthy." }
        "unhealthy" { Write-Failure "Neo4j container is running but 'unhealthy'." }
        "starting" { Write-Warning "Neo4j container is still 'starting'." }
        "not-configured" {
            if (-not $neo4jPassword) {
                Write-Warning "Container does not have a health check. Cannot suggest one as NEO4J_PASSWORD is not in .env."
            } else {
                Write-Warning "Container does not have a health check. To add one, update your docker-compose.yml:
                healthcheck:
                  test: ['CMD', 'cypher-shell', '-u', '$neo4jUser', '-p', '$neo4jPassword', 'RETURN 1']
                  interval: 30s
                  timeout: 10s
                  retries: 5"
            }
        }
    }
}

# ---------------------------------
# 2. POETRY ENVIRONMENT CHECKS
# ---------------------------------
# (... No changes to this section.)
Write-Check "Poetry virtual environment..."
if (-not $env:VIRTUAL_ENV) {
    Write-Failure "'.venv' is not active. This script should be run *after* sourcing 'activate-omega'."
} else {
    Write-Success "'.venv' is active: $env:VIRTUAL_ENV"
}
Write-Check "Poetry dependencies..."
$syncOutput = ""
$syncError = ""
$syncProcess = Start-Process poetry -ArgumentList "install", "--dry-run", "--no-root" -NoNewWindow -RedirectStandardOutput "sync_stdout.txt" -RedirectStandardError "sync_stderr.txt" -Wait -PassThru
$syncOutput = Get-Content "sync_stdout.txt" -Raw
$syncError = Get-Content "sync_stderr.txt" -Raw
Remove-Item "sync_stdout.txt","sync_stderr.txt" -ErrorAction SilentlyContinue
if ($syncProcess.ExitCode -ne 0) {
    if ($syncOutput -like "*Dependencies are locked*") {
        Write-Warning "Dependencies are out of sync. Running 'poetry install'..."
        poetry install --no-root | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Success "Dependencies synced." }
        else { Write-Failure "Failed to sync dependencies. Run 'poetry install' manually." }
    } else { Write-Failure "'poetry install --dry-run' failed. Error output:`n$syncError" }
} else { Write-Success "Dependencies are in sync." }

# ---------------------------------
# 3. SHELL INTEGRATION CHECK
# ---------------------------------
# (... No changes to this section.)
Write-Check "Shell integration..."
if (-not (Get-Command activate-omega -ErrorAction SilentlyContinue)) {
    Write-Warning "The 'activate-omega' function itself was not found. Shell integration may be broken."
} else {
    Write-Success "'activate-omega' function is loaded."
}
@( "pytest", "pytest-cov", "pydantic", "pre-commit" ) | ForEach-Object {
    poetry show $_ --no-interaction > $null 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Failure "$_ is not installed in the venv." }
}
Write-Success "Core Python tooling (pytest, pytest-cov, pydantic, pre-commit) is installed."
$trunkCheck = Get-Command trunk -ErrorAction SilentlyContinue
if (-not $trunkCheck) { Write-Failure "Trunk.io binary is not available in your PATH." }
else { Write-Success "Trunk.io binary is available." }


# ---------------------------------
# FINAL DECISION BLOCK
# ---------------------------------
if ($global:allChecksPassed) {
    Write-Host ""
    Write-Host "--- ALL PRE-FLIGHT CHECKS PASSED ---" -ForegroundColor Green
    Write-Host ""

    # ---------------------------------
    # 5. SERVER START-UP
    # ---------------------------------

    $serverHost = if ($env:CAPTURE_SERVER_HOST) { $env:CAPTURE_SERVER_HOST } else { "127.0.0.1" }
    $serverPort = if ($env:CAPTURE_SERVER_PORT) { $env:CAPTURE_SERVER_PORT } else { 8765 }
    $serverModule = if ($env:CAPTURE_SERVER_MODULE) { $env:CAPTURE_SERVER_MODULE } else { "omega_kg.capture_server:app" }

    $title = "Omega_KG Server"
    $message = "All checks passed. Start the FastAPI server ($serverModule) on $serverHost`:$serverPort?"

    # --- FIX 1: Unambiguous hotkeys ---
    $newWindow = [System.Management.Automation.Host.ChoiceDescription]::new("&New Window", "Start uvicorn in a new, separate terminal window.")
    $thisTerminal = [System.Management.Automation.Host.ChoiceDescription]::new("&This Terminal", "Start uvicorn in this terminal (blocks prompt).")
    $exitChoice = [System.Management.Automation.Host.ChoiceDescription]::new("&Exit (Do not start)", "Do not start the server.")
    $syncNote = [System.Management.Automation.Host.ChoiceDescription]::new("&Sync Note", "Sync an Obsidian note to Linear.")
    $options = [System.Management.Automation.Host.ChoiceDescription[]]($newWindow, $thisTerminal, $exitChoice, $syncNote)
    $default = 0 # Default to New Window

    $result = $host.ui.PromptForChoice($title, $message, $options, $default)

    # --- FIX 2: Call the script that has the "is running" check ---
    $startScriptPath = Join-Path $PSScriptRoot "start-capture-server.ps1"

    switch ($result) {
        0 {
            Write-Info "Starting server in new window (via start-capture-server.ps1)..."
            # This script already starts in a new job, so just call it.
            & $startScriptPath
        }
        1 {
            Write-Info "Starting server in this terminal. (Press Ctrl+C to stop)"

            # We must *manually* check if it's running, since we aren't using the other script
            $existing = Get-CimInstance Win32_Process -Filter "Name = 'uvicorn.exe'" |
                Where-Object { $_.CommandLine -match "omega_kg.capture_server" }

            if ($existing) {
                Write-Warning "⚠ Capture server already running (PID: $($existing.Id))"
            } else {
                # We are already activated, just run the command
                poetry run uvicorn $serverModule --host $serverHost --port $serverPort
            }
        }
        2 {
            Write-Info "Server not started."
        }
        3 {
            Write-Info "Syncing a note to Linear..."
            $notePath = Read-Host "Enter the path to the Obsidian note (e.g., Tasks/MyTask.md)"
            if ($notePath) {
                $syncScript = Join-Path $PSScriptRoot "sync_linear.py"
                poetry run python $syncScript "$notePath"
            } else {
                Write-Warning "No path provided. Aborting sync."
            }
        }
    }
} else {
    Write-Host ""
    Write-Host "--- PRE-FLIGHT CHECKS FAILED ---" -ForegroundColor Red
    Write-Host "Server start-up aborted. Please fix the errors above." -ForegroundColor Red
}
