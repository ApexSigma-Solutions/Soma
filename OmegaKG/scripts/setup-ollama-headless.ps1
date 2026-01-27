# Ollama Headless Horsemen Setup Script
# Phase 1: Environment & Network Configuration
# Phase 2: Headless Startup Configuration

# Requires PowerShell 5.1+ and Administrator privileges
$ErrorActionPreference = "Stop"

Write-Host "🚀 Ollama Headless Horsemen Setup" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Check if running as Administrator
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Error "This script must be run as Administrator. Please re-run with elevated privileges."
    exit 1
}

# Phase 1: Environment & Network Configuration
Write-Host "`n📋 Phase 1: Environment & Network Configuration" -ForegroundColor Yellow

# 1. Set the bind address to all interfaces
Write-Host "Setting OLLAMA_HOST to 0.0.0.0:11434..." -ForegroundColor Cyan
[Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'Machine')
Write-Host "✓ OLLAMA_HOST environment variable set" -ForegroundColor Green

# 2. Optional: Set OLLAMA_MODELS path (commented out by default)
# Write-Host "Setting OLLAMA_MODELS to D:\OllamaModels..." -ForegroundColor Cyan
# [Environment]::SetEnvironmentVariable('OLLAMA_MODELS', 'D:\OllamaModels', 'Machine')
# Write-Host "✓ OLLAMA_MODELS environment variable set" -ForegroundColor Green

# 3. Open the port in Windows Defender Firewall
Write-Host "Configuring Windows Firewall for port 11434..." -ForegroundColor Cyan
$firewallRule = Get-NetFirewallRule -DisplayName "Ollama Server" -ErrorAction SilentlyContinue
if ($null -eq $firewallRule) {
    New-NetFirewallRule -DisplayName "Ollama Server" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
    Write-Host "✓ Windows Firewall rule created" -ForegroundColor Green
} else {
    Write-Host "✓ Windows Firewall rule already exists" -ForegroundColor Yellow
}

# Phase 2: Headless Startup Configuration
Write-Host "`n⚙️  Phase 2: Headless Startup Configuration" -ForegroundColor Yellow

# 1. Disable the default Ollama Startup app
Write-Host "Disabling default Ollama Startup app..." -ForegroundColor Cyan
$startupKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$ollamaStartup = Get-ItemProperty -Path $startupKey -Name "Ollama" -ErrorAction SilentlyContinue
if ($ollamaStartup -and $ollamaStartup.Ollama) {
    Remove-ItemProperty -Path $startupKey -Name "Ollama" -ErrorAction SilentlyContinue
    Write-Host "✓ Default Ollama Startup app disabled" -ForegroundColor Green
} else {
    Write-Host "✓ No default Ollama Startup app found (already disabled)" -ForegroundColor Yellow
}

# 2. Create the Background Task
Write-Host "Creating OllamaService scheduled task..." -ForegroundColor Cyan
$taskName = "OllamaService"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($null -eq $existingTask) {
    $action = New-ScheduledTaskAction -Execute "ollama" -Argument "serve"
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -ExecutionTimeLimit 0

    # Register the task to run as the SYSTEM account (highest privilege, no login required)
    Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName $taskName -User "SYSTEM" -RunLevel Highest
    Write-Host "✓ OllamaService scheduled task created" -ForegroundColor Green
} else {
    Write-Host "✓ OllamaService scheduled task already exists" -ForegroundColor Yellow
}

Write-Host "`n🎉 Setup Complete!" -ForegroundColor Green
Write-Host "================" -ForegroundColor Green
Write-Host "• OLLAMA_HOST set to 0.0.0.0:11434" -ForegroundColor Cyan
Write-Host "• Port 11434 opened in Windows Firewall" -ForegroundColor Cyan
Write-Host "• OllamaService scheduled task created (runs as SYSTEM at startup)" -ForegroundColor Cyan
Write-Host "• Default Ollama Startup app disabled" -ForegroundColor Cyan

Write-Host "`n⚠️  Important Notes:" -ForegroundColor Red
Write-Host "• Restart your computer for environment variables to take effect" -ForegroundColor Yellow
Write-Host "• After restart, Ollama will run as a headless service on port 11434" -ForegroundColor Yellow
Write-Host "• Use the verification script to test the setup" -ForegroundColor Yellow

Write-Host "`nNext steps:" -ForegroundColor Green
Write-Host "1. Restart your computer" -ForegroundColor Cyan
Write-Host "2. Run: .\scripts\verify-ollama-service.ps1" -ForegroundColor Cyan
Write-Host "3. Configure Omega_KG integration" -ForegroundColor Cyan
