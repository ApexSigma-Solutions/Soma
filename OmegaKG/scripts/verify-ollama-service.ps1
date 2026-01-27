# Ollama Service Verification Script
# Phase 3: The MAR Protocol (Verification)

$ErrorActionPreference = "Stop"

Write-Host "🔍 Ollama Service Verification (MAR Protocol)" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Get the current machine's IP addresses
$ipAddresses = Get-NetIPAddress | Where-Object {
    $_.AddressFamily -eq 'IPv4' -and
    $_.IPAddress -notlike '127.*' -and
    $_.IPAddress -notlike '169.254.*' -and
    $_.PrefixOrigin -ne 'WellKnown'
} | Select-Object -ExpandProperty IPAddress

Write-Host "`n📋 Phase 3: Verification Protocol" -ForegroundColor Yellow

# 1. Local Check: Check if the port is listening
Write-Host "1. Local Port Check..." -ForegroundColor Cyan
$portCheck = netstat -an | Where-Object { $_ -match "11434" }
if ($portCheck -match "0.0.0.0:11434") {
    Write-Host "✓ Port 11434 is listening on 0.0.0.0" -ForegroundColor Green
} elseif ($portCheck -match "127.0.0.1:11434") {
    Write-Host "⚠️  Port 11434 is only listening on 127.0.0.1 (should be 0.0.0.0)" -ForegroundColor Yellow
} else {
    Write-Host "❌ Port 11434 is not listening" -ForegroundColor Red
}

# 2. Service Check: Check if Ollama service is running
Write-Host "`n2. Service Status Check..." -ForegroundColor Cyan
$taskStatus = Get-ScheduledTask -TaskName "OllamaService" -ErrorAction SilentlyContinue
if ($taskStatus) {
    $taskInfo = $taskStatus | Get-ScheduledTaskInfo
    Write-Host "✓ OllamaService scheduled task exists" -ForegroundColor Green
    Write-Host "  Last Run Time: $($taskInfo.LastRunTime)" -ForegroundColor Cyan
    Write-Host "  Last Task Result: $($taskInfo.LastTaskResult)" -ForegroundColor Cyan
    Write-Host "  Number of Missed Runs: $($taskInfo.NumberOfMissedRuns)" -ForegroundColor Cyan
} else {
    Write-Host "❌ OllamaService scheduled task not found" -ForegroundColor Red
}

# Check if ollama process is running
$ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaProcess) {
    Write-Host "✓ Ollama process is running (PID: $($ollamaProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "❌ Ollama process is not running" -ForegroundColor Red
}

# 3. API Root Check: Test if Ollama API is responding
Write-Host "`n3. API Root Check..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/" -Method Get -TimeoutSec 10
    if ($response -eq "Ollama is running") {
        Write-Host "✓ Ollama API is responding: $response" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Unexpected API response: $response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Ollama API is not responding: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Network Check: Test from local network (if available)
if ($ipAddresses.Count -gt 0) {
    Write-Host "`n4. Network Accessibility Check..." -ForegroundColor Cyan
    foreach ($ip in $ipAddresses) {
        try {
            $response = Invoke-RestMethod -Uri "http://$($ip):11434/" -Method Get -TimeoutSec 5
            Write-Host "✓ Ollama is accessible from network IP $($ip): $($response)" -ForegroundColor Green
            break
        } catch {
            Write-Host "⚠️  Ollama not accessible from network IP $($ip): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "`n4. Network Accessibility Check..." -ForegroundColor Cyan
    Write-Host "⚠️  No network IP addresses found (likely running on localhost only)" -ForegroundColor Yellow
}

# 5. Inference Check: Test actual model inference
Write-Host "`n5. Inference Test..." -ForegroundColor Cyan
try {
    $testBody = @{
        model = "llama3.2"
        prompt = "System check. Status?"
        stream = $false
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $testBody -ContentType "application/json" -TimeoutSec 30
    if ($response.response) {
        Write-Host "✓ Model inference successful" -ForegroundColor Green
        Write-Host "  Response: $($response.response.Substring(0, [Math]::Min(50, $response.response.Length)))..." -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  Unexpected inference response: $response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Model inference failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Note: This may be expected if 'llama3.2' model is not installed yet" -ForegroundColor Yellow
}

# 6. Scheduled Task Details
Write-Host "`n6. Scheduled Task Details..." -ForegroundColor Cyan
if ($taskStatus) {
    $taskDetails = $taskStatus | Select-Object TaskName, State, Author, Description
    Write-Host "  Task Name: $($taskDetails.TaskName)" -ForegroundColor Cyan
    Write-Host "  State: $($taskDetails.State)" -ForegroundColor Cyan
    Write-Host "  Author: $($taskDetails.Author)" -ForegroundColor Cyan
    Write-Host "  Description: $($taskDetails.Description)" -ForegroundColor Cyan
}

Write-Host "`n🎉 Verification Complete!" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Green

# Summary
Write-Host "`n📋 Summary:" -ForegroundColor Yellow
Write-Host "• Check if Ollama is running as a service" -ForegroundColor Cyan
Write-Host "• Verify port 11434 is accessible from network" -ForegroundColor Cyan
Write-Host "• Test API endpoints are responding" -ForegroundColor Cyan
Write-Host "• Confirm model inference works (if models are installed)" -ForegroundColor Cyan

Write-Host "`n🔧 Troubleshooting:" -ForegroundColor Red
Write-Host "• If port is not listening, restart your computer" -ForegroundColor Yellow
Write-Host "• If API is not responding, check Ollama service status" -ForegroundColor Yellow
Write-Host "• If network access fails, check Windows Firewall rules" -ForegroundColor Yellow
Write-Host "• If inference fails, pull a model: ollama pull llama3.2" -ForegroundColor Yellow
