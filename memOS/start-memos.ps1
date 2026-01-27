# =============================================================================
# memOS.MCP Quick Start Script for Windows
# =============================================================================
# This script starts all required infrastructure services for memOS.MCP
# =============================================================================

param(
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Status,
    [switch]$Logs,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ComposeFile = "docker-compose.yml"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to project directory
Push-Location $ProjectDir

function Write-Header {
    param([string]$Message)
    Write-Host "`n==============================================================================" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "==============================================================================`n" -ForegroundColor Cyan
}

function Test-Docker {
    try {
        docker --version | Out-Null
        return $true
    } catch {
        Write-Host "❌ Docker is not installed or not running" -ForegroundColor Red
        Write-Host "   Please install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        return $false
    }
}

function Test-Service {
    param(
        [string]$Name,
        [string]$Url,
        [int]$MaxRetries = 10
    )
    
    Write-Host "Checking $Name... " -NoNewline
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            Write-Host "✅ Online" -ForegroundColor Green
            return $true
        } catch {
            if ($i -eq $MaxRetries) {
                Write-Host "❌ Not responding" -ForegroundColor Red
                return $false
            }
            Start-Sleep -Seconds 2
        }
    }
}

function Start-Services {
    Write-Header "Starting memOS.MCP Infrastructure"
    
    if (-not (Test-Docker)) {
        exit 1
    }
    
    Write-Host "Starting services (this may take a few minutes on first run)..." -ForegroundColor Yellow
    docker-compose up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n❌ Failed to start services" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`nWaiting for services to become healthy..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    Write-Host "`nService Health Check:" -ForegroundColor Cyan
    Test-Service "Redis" "http://localhost:6379" | Out-Null
    Test-Service "PostgreSQL" "http://localhost:5800" | Out-Null
    Test-Service "Ollama" "http://localhost:11434/api/tags" | Out-Null
    
    Write-Host "`n✅ All services started successfully!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Verify: " -NoNewline
    Write-Host ".\start-memos.ps1 -Status" -ForegroundColor Yellow
    Write-Host "  2. Initialize DB: " -NoNewline
    Write-Host "poetry run python scripts\init_db.py" -ForegroundColor Yellow
    Write-Host "  3. Start memOS: " -NoNewline
    Write-Host "poetry run python -m memos_mcp --sse" -ForegroundColor Yellow
}

function Stop-Services {
    Write-Header "Stopping memOS.MCP Infrastructure"
    
    docker-compose down
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ All services stopped" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to stop services" -ForegroundColor Red
        exit 1
    }
}

function Restart-Services {
    Write-Header "Restarting memOS.MCP Infrastructure"
    
    Stop-Services
    Start-Sleep -Seconds 2
    Start-Services
}

function Show-Status {
    Write-Header "memOS.MCP Infrastructure Status"
    
    if (-not (Test-Docker)) {
        exit 1
    }
    
    Write-Host "Container Status:" -ForegroundColor Cyan
    docker-compose ps
    
    Write-Host "`nService Health:" -ForegroundColor Cyan
    
    # Redis
    try {
        $redisInfo = docker exec memos-redis redis-cli INFO server 2>$null | Select-String "redis_version"
        if ($redisInfo) {
            Write-Host "  Redis:      " -NoNewline
            Write-Host "✅ Running ($redisInfo)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Redis:      " -NoNewline
        Write-Host "❌ Not running" -ForegroundColor Red
    }
    
    # PostgreSQL
    try {
        $pgVersion = docker exec memos-postgres psql -U omega_user -d omega_kg_stable -c "SELECT version();" 2>$null
        if ($pgVersion) {
            Write-Host "  PostgreSQL: " -NoNewline
            Write-Host "✅ Running" -ForegroundColor Green
        }
    } catch {
        Write-Host "  PostgreSQL: " -NoNewline
        Write-Host "❌ Not running" -ForegroundColor Red
    }
    
    # Ollama
    try {
        $ollamaModels = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
        $hasBgeM3 = $ollamaModels.models | Where-Object { $_.name -like "*bge-m3*" }
        
        Write-Host "  Ollama:     " -NoNewline
        if ($hasBgeM3) {
            Write-Host "✅ Running (bge-m3 ready)" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Running (bge-m3 not found)" -ForegroundColor Yellow
            Write-Host "              Run: docker exec memos-ollama ollama pull bge-m3" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Ollama:     " -NoNewline
        Write-Host "❌ Not running" -ForegroundColor Red
    }
    
    Write-Host "`nConnection Endpoints:" -ForegroundColor Cyan
    Write-Host "  Redis:      redis://localhost:6379" -ForegroundColor White
    Write-Host "  PostgreSQL: postgresql://omega_user@localhost:5800/omega_kg_stable" -ForegroundColor White
    Write-Host "  Ollama:     http://localhost:11434" -ForegroundColor White
}

function Show-Logs {
    Write-Header "memOS.MCP Infrastructure Logs"
    
    Write-Host "Following logs (Ctrl+C to stop)..." -ForegroundColor Yellow
    docker-compose logs -f
}

function Clean-All {
    Write-Header "Cleaning memOS.MCP Infrastructure"
    
    Write-Host "⚠️  WARNING: This will delete all data!" -ForegroundColor Red
    Write-Host "   - Redis data" -ForegroundColor Yellow
    Write-Host "   - PostgreSQL data" -ForegroundColor Yellow
    Write-Host "   - Ollama models" -ForegroundColor Yellow
    Write-Host ""
    
    $confirm = Read-Host "Are you sure? Type 'yes' to confirm"
    
    if ($confirm -eq "yes") {
        Write-Host "`nStopping and removing all containers and volumes..." -ForegroundColor Yellow
        docker-compose down -v
        
        Write-Host "✅ All data cleaned" -ForegroundColor Green
    } else {
        Write-Host "❌ Cancelled" -ForegroundColor Red
    }
}

# =============================================================================
# Main Script Logic
# =============================================================================

try {
    if ($Stop) {
        Stop-Services
    } elseif ($Restart) {
        Restart-Services
    } elseif ($Status) {
        Show-Status
    } elseif ($Logs) {
        Show-Logs
    } elseif ($Clean) {
        Clean-All
    } else {
        Start-Services
    }
} finally {
    Pop-Location
}
