# =============================================================================
# memOS.MCP Server Startup Script
# =============================================================================
# Starts the memOS.MCP server in SSE mode on port 8768
# =============================================================================

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host " memOS.MCP Server Startup" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ProjectDir

# Verify prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow
Write-Host ""

# Check Redis
try {
    $redisTest = Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($redisTest.TcpTestSucceeded) {
        Write-Host "  ✅ Redis running on port 6379" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Redis not running on port 6379" -ForegroundColor Red
        Write-Host "     Start with: docker run -d -p 6379:6379 --name memos-redis redis:7-alpine" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  ⚠️  Could not check Redis status" -ForegroundColor Yellow
}

# Check Ollama
try {
    $ollamaTest = Test-NetConnection -ComputerName localhost -Port 11434 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($ollamaTest.TcpTestSucceeded) {
        Write-Host "  ✅ Ollama running on port 11434" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Ollama not running on port 11434" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ⚠️  Could not check Ollama status" -ForegroundColor Yellow
}

# Check PostgreSQL
try {
    $pgTest = Test-NetConnection -ComputerName localhost -Port 5800 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($pgTest.TcpTestSucceeded) {
        Write-Host "  ✅ PostgreSQL running on port 5800" -ForegroundColor Green
    } else {
        Write-Host "  ❌ PostgreSQL not running on port 5800" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ⚠️  Could not check PostgreSQL status" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting memOS.MCP server on port 8768..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Start server
try {
    poetry run python src/memos_mcp/server.py
} finally {
    Pop-Location
}
