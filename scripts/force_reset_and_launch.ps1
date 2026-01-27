# Soma Stack: Full Reset & Launch Script (PS7-preview)
# Purpose: Kill existing services, fix venv, migrate DB, and launch.
# Strategy: Manual .venv override due to Poetry TLS/Cert issues.
# Version: 1.2 - Added psycopg2-binary for SQLAlchemy/Alembic

$ErrorActionPreference = "Stop"
$SOMA_ROOT = "D:\projects\Soma"
$INGRESS_ROOT = "$SOMA_ROOT\InGress"

# CRITICAL: Correct password from .env (omega_dev_password, not password)
$DSN = "postgresql://omega_user:omega_dev_password@localhost:6000/omega_kg_stable"

Write-Host "--- [SOMA] Starting Force Reset Protocol v1.2 ---" -ForegroundColor Cyan

# 0. Clear stale SSL/TLS environment variables (Poetry residue)
Write-Host "[0/5] Clearing stale SSL certificate paths..." -ForegroundColor DarkGray
$env:REQUESTS_CA_BUNDLE = $null
$env:SSL_CERT_FILE = $null
$env:CURL_CA_BUNDLE = $null

# 1. Kill Zombies (Port-based cleanup)
Write-Host "[1/5] Terminating existing processes on 8000 (InGress), 8765 (OmegaKG)..." -ForegroundColor Yellow
$ports = @(8000, 8765)
foreach ($port in $ports) {
    try {
        $proc = Get-NetTCPConnection -LocalPort $port -ErrorAction Stop
        if ($proc) {
            Stop-Process -Id $proc.OwningProcess -Force
            Write-Host "      Killed process on port $port" -ForegroundColor Gray
        }
    }
    catch {
        # Port not in use, skip
    }
}

# 2. Venv Restoration (Manual Safety Hatch)
Write-Host "[2/5] Checking .venv at $INGRESS_ROOT..." -ForegroundColor Yellow
Set-Location $INGRESS_ROOT
if (-not (Test-Path ".venv")) {
    Write-Host "      Creating manual .venv (Poetry bypass strategy)..." -ForegroundColor Magenta
    python -m venv .venv
}

# Activate for the current session
& ".\.venv\Scripts\Activate.ps1"

# 3. Dependency Injection (with cert fix applied)
# NOTE: psycopg2-binary needed for SQLAlchemy sync driver (Alembic uses this)
#       asyncpg is for async FastAPI connections
Write-Host "[3/5] Installing core dependencies via PIP..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
python -m pip install fastapi uvicorn asyncpg psycopg2-binary alembic sqlalchemy pydantic-settings structlog psutil watchdog requests --quiet
Write-Host "      Dependencies installed." -ForegroundColor Gray

# 4. Database Peristalsis (Migration)
Write-Host "[4/5] Running Alembic Migrations to sync Raw Lake..." -ForegroundColor Yellow
$env:SOMA_PG_DSN = $DSN
# Ensure we are in InGress directory where alembic.ini lives
Set-Location $INGRESS_ROOT
alembic upgrade head

# 5. Launch InGress Only (Minimal viable stack)
Write-Host "[5/5] Launching InGress (Senses) + Stomach (Poller)..." -ForegroundColor Green
Set-Location $INGRESS_ROOT

# Use the venv python for both services
$VENV_PYTHON = "$INGRESS_ROOT\.venv\Scripts\python.exe"

# Launch InGress (FastAPI on port 8000)
Start-Process -FilePath $VENV_PYTHON -ArgumentList "soma_ingress/main.py" -WorkingDirectory $INGRESS_ROOT -WindowStyle Normal

# Wait a moment for InGress to bind
Start-Sleep -Seconds 2

# Launch Stomach (Poller)
Start-Process -FilePath $VENV_PYTHON -ArgumentList "soma_ingress/raw_lake_poller.py" -WorkingDirectory $INGRESS_ROOT -WindowStyle Normal

Write-Host "--- [SOMA] InGress + Stomach Launched. Use Orchestrator for full stack. ---" -ForegroundColor Cyan
Write-Host "    InGress Health: http://localhost:8000/health" -ForegroundColor DarkCyan
