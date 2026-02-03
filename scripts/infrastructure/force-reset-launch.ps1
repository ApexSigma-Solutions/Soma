# Soma Stack: The "Antigravity" Reset Protocol v1.3.7
# Purpose: Deep environmental cleansing, fresh DBs, and stable orchestration.
# Strategy: Aggressive TLS scrubbing + Process tree termination + Start-Command fix.

$ErrorActionPreference = "Stop"
$SOMA_ROOT = "D:\projects\Soma"
$INGRESS_ROOT = "$SOMA_ROOT\InGress"

# --- CONFIGURATION ---
$DB_USER = "omega_user"
$DB_PASS = "omega_dev_password"
$PG_CONTAINER = "apexsigma.postgres.soma"
$NEO_CONTAINER = "apexsigma.neo4j.soma"
$DSN = "postgresql://${DB_USER}:${DB_PASS}@localhost:6000/soma_sensory_lake"

Write-Host "--- [SOMA] Executing ANTIGRAVITY Protocol v1.3.7 ---" -ForegroundColor Cyan

# 1. TLS Environmental Cleansing (The "Ghost" Exorcism)
Write-Host "[1/7] Exorcising TLS ghosts and stale cert paths..." -ForegroundColor Yellow
$env:SSL_CERT_FILE = ""
$env:REQUESTS_CA_BUNDLE = ""
$env:PIP_CERT = ""
# Explicitly tell pip to ignore the broken certifi path for this session if it persists
$env:PYTHONHTTPSVERIFY = "0" 

# 2. Nuclear Process Termination
Write-Host "[2/7] Terminating all zombie Python, Uvicorn, and Cloudflared processes..." -ForegroundColor Yellow
$killList = @("python", "uvicorn", "cloudflared", "conhost")
foreach ($name in $killList) {
    Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

# Clear ports specifically (6000 for PG, 7474/7687 for Neo4j)
$targetPorts = @(6000, 7474, 7687, 8000, 8765)
foreach ($port in $targetPorts) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conns) {
        $conns | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
}

# 3. Fresh Database Stack (Docker)
Write-Host "[3/7] Hard-resetting apexsigma containers..." -ForegroundColor Yellow
docker stop $PG_CONTAINER $NEO_CONTAINER 2>$null
docker rm -f $PG_CONTAINER $NEO_CONTAINER 2>$null
Start-Sleep -Seconds 2

# Launch fresh Postgres with distinct volume
docker run -d --name $PG_CONTAINER -p 6000:5432 `
    -v soma_pg_data:/var/lib/postgresql/data `
    -e POSTGRES_USER=$DB_USER -e POSTGRES_PASSWORD=$DB_PASS -e POSTGRES_DB=soma_sensory_lake postgres:16-alpine

# Launch fresh Neo4j with distinct volume and APOC
docker run -d --name $NEO_CONTAINER -p 7474:7474 -p 7687:7687 `
    -v soma_neo4j_data:/data -v soma_neo4j_logs:/logs `
    -e NEO4J_AUTH=$("${DB_USER}/${DB_PASS}") -e NEO4J_PLUGINS='["apoc"]' neo4j:latest

# 4. The "86" - Venv Nuke with Retry
Write-Host "[4/7] 86ing the poisoned venv (with lock-breaking)..." -ForegroundColor Red
if (Test-Path "$INGRESS_ROOT\.venv") {
    try {
        Remove-Item -Recurse -Force "$INGRESS_ROOT\.venv"
    }
    catch {
        Write-Host "      Handle still locked. Waiting 5s for OS release..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
        Remove-Item -Recurse -Force "$INGRESS_ROOT\.venv"
    }
}

# 5. Rebuild (Manual Safety Hatch)
Write-Host "[5/7] Rebuilding environment (Manual Pip Hatch)..." -ForegroundColor Yellow
cd $INGRESS_ROOT
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"

# We use --trusted-host to bypass the TLS certifi error if the environment is still being 'kak'
python -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org
python -m pip install fastapi uvicorn asyncpg alembic sqlalchemy pydantic-settings structlog psutil watchdog requests psycopg2-binary neo4j mcp --trusted-host pypi.org --trusted-host files.pythonhosted.org

# 6. Fresh Alembic Init
Write-Host "[6/7] Initializing Fresh Migration History..." -ForegroundColor Yellow
if (Test-Path "alembic") { Remove-Item -Recurse -Force "alembic"; Remove-Item "alembic.ini" }
alembic init alembic
(Get-Content "alembic.ini") -replace "sqlalchemy.url = .*", "sqlalchemy.url = $DSN" | Set-Content "alembic.ini"

# 7. Execute Orchestrator
Write-Host "[7/7] Launching Orchestrator v2.9..." -ForegroundColor Green
cd $SOMA_ROOT
$VENV_PYTHON = "$INGRESS_ROOT\.venv\Scripts\python.exe"

# FIXED: Ensure the path to python is fully quoted and the start command is robust
$cmd = "cmd /c start `"SOMA_EXECUTIVE`" `"$VENV_PYTHON`" orchestrator.py"
Invoke-Expression $cmd

Write-Host "--- [SOMA] Antigravity Launch Successful. ---" -ForegroundColor Cyan