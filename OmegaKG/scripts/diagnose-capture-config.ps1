# ==============================================================================
# Omega_KG Capture Server Configuration Diagnostic
# ==============================================================================
# Validates port alignment, authentication setup, and server readiness
# Run before starting the capture server to catch configuration issues
# ==============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Omega_KG Capture Server - Configuration Diagnostic       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$issues = @()
$warnings = @()

# ==============================================================================
# 1. Check .env File
# ==============================================================================

Write-Host "📄 Checking .env configuration..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    $issues += ".env file not found"
    Write-Host "   ❌ .env file not found!" -ForegroundColor Red
    Write-Host "   📝 Copy .env.example to .env and configure it" -ForegroundColor Gray
} else {
    Write-Host "   ✅ .env file exists" -ForegroundColor Green
    
    # Read .env file
    $envContent = Get-Content ".env" -Raw
    
    # Check critical variables
    $criticalVars = @{
        "APP_PORT" = "8765"
        "APP_HOST" = "127.0.0.1"
        "NEO4J_PASSWORD" = $null
        "JWT_SECRET_KEY" = $null
    }
    
    # Check EXTENSION_API_KEY (supports both PRD and regular variants)
    $extensionKeyFound = $false
    if ($envContent -match "EXTENSION_API_KEY(_PRD)?=(.+)") {
        $extensionKeyFound = $true
        Write-Host "   ✅ EXTENSION_API_KEY is configured" -ForegroundColor Green
    }
    
    if (-not $extensionKeyFound) {
        $issues += "EXTENSION_API_KEY not found in .env"
    }
    
    foreach ($var in $criticalVars.Keys) {
        if ($envContent -match "$var=(.+)") {
            $value = $matches[1].Trim()
            
            # Check for placeholder values
            if ($value -match "change_me|placeholder|your_|<.*>") {
                $warnings += "$var appears to use a placeholder value"
                Write-Host "   ⚠️  $var needs configuration (currently: $value)" -ForegroundColor Yellow
            } elseif ($value -eq "") {
                $warnings += "$var is empty"
                Write-Host "   ⚠️  $var is empty" -ForegroundColor Yellow
            } else {
                Write-Host "   ✅ $var is configured" -ForegroundColor Green
                
                # Store actual values for comparison
                if ($var -eq "APP_PORT") {
                    $envPort = $value
                } elseif ($var -eq "APP_HOST") {
                    $envHost = $value
                }
            }
        } else {
            $issues += "$var not found in .env"
            Write-Host "   ❌ $var not found in .env" -ForegroundColor Red
        }
    }
}

# ==============================================================================
# 2. Check Chrome Extension Configuration
# ==============================================================================

Write-Host ""
Write-Host "🔧 Checking Chrome extension configuration..." -ForegroundColor Yellow

$configJsPath = "chrome-extension\config.js"
if (-not (Test-Path $configJsPath)) {
    $warnings += "Chrome extension config.js not found"
    Write-Host "   ⚠️  config.js not found at $configJsPath" -ForegroundColor Yellow
} else {
    $configContent = Get-Content $configJsPath -Raw
    
    # Extract SERVER_URL
    if ($configContent -match "SERVER_URL:\s*'([^']+)'") {
        $extensionUrl = $matches[1]
        Write-Host "   ✅ Extension SERVER_URL: $extensionUrl" -ForegroundColor Green
        
        # Check port alignment
        if ($envPort -and $extensionUrl -match ":(\d+)") {
            $extensionPort = $matches[1]
            if ($extensionPort -ne $envPort) {
                $issues += "Port mismatch: .env=$envPort, extension=$extensionPort"
                Write-Host "   ❌ PORT MISMATCH! .env uses $envPort, extension uses $extensionPort" -ForegroundColor Red
            } else {
                Write-Host "   ✅ Port alignment verified: $envPort" -ForegroundColor Green
            }
        }
    } else {
        $warnings += "Could not parse SERVER_URL from config.js"
        Write-Host "   ⚠️  Could not parse SERVER_URL from config.js" -ForegroundColor Yellow
    }
}

# ==============================================================================
# 3. Check for Port Conflicts
# ==============================================================================

Write-Host ""
Write-Host "🔍 Checking for port conflicts..." -ForegroundColor Yellow

if ($envPort) {
    $portInUse = Get-NetTCPConnection -LocalPort $envPort -State Listen -ErrorAction SilentlyContinue
    
    if ($portInUse) {
        $process = Get-Process -Id $portInUse.OwningProcess -ErrorAction SilentlyContinue
        $warnings += "Port $envPort is already in use by $($process.ProcessName)"
        Write-Host "   ⚠️  Port $envPort is in use by $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Yellow
    } else {
        Write-Host "   ✅ Port $envPort is available" -ForegroundColor Green
    }
}

# ==============================================================================
# 4. Check Neo4j Connection
# ==============================================================================

Write-Host ""
Write-Host "🔗 Checking Neo4j availability..." -ForegroundColor Yellow

$neo4jPort = 7687
$neo4jConnection = Get-NetTCPConnection -LocalPort $neo4jPort -State Listen -ErrorAction SilentlyContinue

if ($neo4jConnection) {
    Write-Host "   ✅ Neo4j is listening on port $neo4jPort" -ForegroundColor Green
} else {
    $warnings += "Neo4j does not appear to be running on port $neo4jPort"
    Write-Host "   ⚠️  Neo4j is not running on port $neo4jPort" -ForegroundColor Yellow
    Write-Host "   📝 Start Neo4j before running the capture server" -ForegroundColor Gray
}

# ==============================================================================
# 5. Check PostgreSQL Connection
# ==============================================================================

Write-Host ""
Write-Host "🐘 Checking PostgreSQL availability..." -ForegroundColor Yellow

$pgPort = 5433
$pgConnection = Get-NetTCPConnection -LocalPort $pgPort -State Listen -ErrorAction SilentlyContinue

if ($pgConnection) {
    Write-Host "   ✅ PostgreSQL is listening on port $pgPort" -ForegroundColor Green
} else {
    $warnings += "PostgreSQL does not appear to be running on port $pgPort"
    Write-Host "   ⚠️  PostgreSQL is not running on port $pgPort" -ForegroundColor Yellow
    Write-Host "   📝 Start PostgreSQL before running the capture server" -ForegroundColor Gray
}

# ==============================================================================
# 6. Check Ollama Service
# ==============================================================================

Write-Host ""
Write-Host "🤖 Checking Ollama embedding service..." -ForegroundColor Yellow

$ollamaPort = 11434
$ollamaConnection = Get-NetTCPConnection -LocalPort $ollamaPort -State Listen -ErrorAction SilentlyContinue

if ($ollamaConnection) {
    Write-Host "   ✅ Ollama is listening on port $ollamaPort" -ForegroundColor Green
    
    # Try to get Ollama version
    try {
        $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:$ollamaPort/api/tags" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "   ✅ Ollama API responding successfully" -ForegroundColor Green
    } catch {
        $warnings += "Ollama port is open but API is not responding"
        Write-Host "   ⚠️  Ollama port is open but API is not responding" -ForegroundColor Yellow
    }
} else {
    $warnings += "Ollama does not appear to be running on port $ollamaPort"
    Write-Host "   ⚠️  Ollama is not running on port $ollamaPort" -ForegroundColor Yellow
    Write-Host "   📝 Embeddings will not work without Ollama" -ForegroundColor Gray
}

# ==============================================================================
# 7. Check Poetry Environment
# ==============================================================================

Write-Host ""
Write-Host "📦 Checking Poetry environment..." -ForegroundColor Yellow

try {
    $poetryVersion = poetry --version 2>&1
    Write-Host "   ✅ Poetry installed: $poetryVersion" -ForegroundColor Green
    
    # Check if dependencies are installed
    $poetryEnv = poetry env info --path 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Virtual environment exists" -ForegroundColor Green
    } else {
        $warnings += "Poetry virtual environment not initialized"
        Write-Host "   ⚠️  Virtual environment not initialized" -ForegroundColor Yellow
        Write-Host "   📝 Run: poetry install" -ForegroundColor Gray
    }
} catch {
    $issues += "Poetry is not installed or not in PATH"
    Write-Host "   ❌ Poetry not found!" -ForegroundColor Red
    Write-Host "   📝 Install Poetry: https://python-poetry.org/docs/#installation" -ForegroundColor Gray
}

# ==============================================================================
# Summary
# ==============================================================================

Write-Host ""
Write-Host "═" * 60 -ForegroundColor Cyan
Write-Host ""

if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✨ CONFIGURATION OK! ✨" -ForegroundColor Green
    Write-Host ""
    Write-Host "All checks passed. You can start the server with:" -ForegroundColor Green
    Write-Host "   .\start-capture-server-window.ps1" -ForegroundColor Cyan
    Write-Host ""
} else {
    if ($issues.Count -gt 0) {
        Write-Host "❌ CRITICAL ISSUES FOUND ($($issues.Count)):" -ForegroundColor Red
        Write-Host ""
        foreach ($issue in $issues) {
            Write-Host "   • $issue" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "⚠️  WARNINGS ($($warnings.Count)):" -ForegroundColor Yellow
        Write-Host ""
        foreach ($warning in $warnings) {
            Write-Host "   • $warning" -ForegroundColor Yellow
        }
        Write-Host ""
    }
    
    if ($issues.Count -gt 0) {
        Write-Host "⛔ Please fix critical issues before starting the server." -ForegroundColor Red
    } else {
        Write-Host "⚠️  You can start the server, but warnings should be addressed." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To proceed anyway:" -ForegroundColor Gray
        Write-Host "   .\start-capture-server-window.ps1" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "═" * 60 -ForegroundColor Cyan
Write-Host ""

# Exit with appropriate code
if ($issues.Count -gt 0) {
    exit 1
} else {
    exit 0
}
