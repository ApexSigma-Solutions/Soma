#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Gracefully restart memOS.MCP server
.DESCRIPTION
    Stops existing memOS.MCP processes and starts a new instance with updated configuration
#>

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "memOS.MCP Graceful Restart" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Find memOS.MCP processes
$memosProcesses = Get-Process | Where-Object { 
    $_.ProcessName -eq "python" -and 
    $_.CommandLine -like "*memos_mcp*" 
}

if ($memosProcesses) {
    Write-Host "Found $($memosProcesses.Count) memOS.MCP process(es)" -ForegroundColor Yellow
    
    foreach ($proc in $memosProcesses) {
        try {
            Write-Host "  Stopping PID $($proc.Id)..." -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        } catch {
            # Process may have already exited
        }
    }
    
    Start-Sleep -Seconds 2
    Write-Host "✅ Stopped existing processes`n" -ForegroundColor Green
} else {
    Write-Host "No existing memOS.MCP processes found`n" -ForegroundColor Gray
}

# Start new instance
Write-Host "🚀 Starting memOS.MCP server..." -ForegroundColor Yellow
Write-Host "   Port: 8768" -ForegroundColor Gray
Write-Host "   Updated Config: InGest-LLM @ localhost:8766" -ForegroundColor Gray
Write-Host "   Updated Config: PostgreSQL @ localhost:6000" -ForegroundColor Gray
Write-Host "   Updated Config: Redis @ localhost:6380`n" -ForegroundColor Gray

Push-Location "d:\projects\OmegaKG\memos.MCP"

try {
    Start-Process -FilePath "python" `
        -ArgumentList "-m", "memos_mcp" `
        -WorkingDirectory "d:\projects\OmegaKG\memos.MCP" `
        -WindowStyle Hidden
    
    Start-Sleep -Seconds 3
    
    # Verify startup
    $newProcess = Get-Process | Where-Object { 
        $_.ProcessName -eq "python" -and 
        $_.CommandLine -like "*memos_mcp*" 
    }
    
    if ($newProcess) {
        Write-Host "✅ memOS.MCP server started successfully" -ForegroundColor Green
        Write-Host "   PID: $($newProcess.Id)" -ForegroundColor Gray
        
        # Test connection
        Start-Sleep -Seconds 2
        Write-Host "`n📊 Testing connectivity..." -ForegroundColor Cyan
        
        try {
            $testResult = Invoke-WebRequest -Uri "http://localhost:8768" -Method GET -TimeoutSec 5 -ErrorAction Stop
            Write-Host "✅ Server responding on port 8768" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  Server started but not responding yet (may need more time)" -ForegroundColor Yellow
        }
        
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "✅ Restart Complete" -ForegroundColor Green
        Write-Host "========================================`n" -ForegroundColor Cyan
        
        exit 0
    } else {
        Write-Host "❌ Failed to start memOS.MCP server" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "❌ Error during restart: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
