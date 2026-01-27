#!/usr/bin/env pwsh
# Restart memOS.MCP Server with updated configuration

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "memOS.MCP Server Restart Script" -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan

$memosMcpPath = "d:\projects\OmegaKG\memos.MCP"

# Stop existing memOS.MCP processes
Write-Host "🛑 Stopping existing memOS.MCP processes..." -ForegroundColor Yellow
Get-Process | Where-Object { 
    $_.ProcessName -eq "python" -and 
    $_.CommandLine -like "*memos_mcp*" 
} | ForEach-Object {
    Write-Host "   Stopping PID $($_.Id)..." -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force
}

Start-Sleep -Seconds 2

# Verify stopped
$stillRunning = Get-Process | Where-Object { 
    $_.ProcessName -eq "python" -and 
    $_.CommandLine -like "*memos_mcp*" 
}

if ($stillRunning) {
    Write-Host "❌ Failed to stop memOS.MCP processes" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Stopped all memOS.MCP processes`n" -ForegroundColor Green

# Start new instance
Write-Host "🚀 Starting memOS.MCP server..." -ForegroundColor Yellow
Push-Location $memosMcpPath

try {
    # Run health check first
    Write-Host "`n📊 Running infrastructure health check..." -ForegroundColor Cyan
    python ..\scripts\infrastructure\health_check.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n⚠️  Some services offline, but continuing..." -ForegroundColor Yellow
    }
    
    Write-Host "`n🎯 Starting memOS.MCP server on port 8768..." -ForegroundColor Cyan
    
    # Start in background
    Start-Process -FilePath "python" -ArgumentList "-m", "memos_mcp" -WorkingDirectory $memosMcpPath -WindowStyle Hidden
    
    Start-Sleep -Seconds 3
    
    # Verify it started
    $memosProcess = Get-Process | Where-Object { 
        $_.ProcessName -eq "python" -and 
        $_.CommandLine -like "*memos_mcp*" 
    }
    
    if ($memosProcess) {
        Write-Host "`n✅ memOS.MCP server started successfully" -ForegroundColor Green
        Write-Host "   PID: $($memosProcess.Id)" -ForegroundColor Gray
        Write-Host "   Port: 8768" -ForegroundColor Gray
        Write-Host "   Transport: SSE (Server-Sent Events)" -ForegroundColor Gray
    } else {
        Write-Host "`n❌ Failed to start memOS.MCP server" -ForegroundColor Red
        exit 1
    }
    
} finally {
    Pop-Location
}

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "✅ Restart complete - memOS.MCP ready for connections" -ForegroundColor Green
Write-Host "===========================================================`n" -ForegroundColor Cyan
