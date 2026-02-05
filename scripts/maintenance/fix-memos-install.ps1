# Fix memOS installation by reinstalling in editable mode
param()

Write-Host "Fixing memOS installation..." -ForegroundColor Cyan

# Clear SSL cert environment variables
$env:CURL_CA_BUNDLE = ''
$env:SSL_CERT_FILE = ''
$env:REQUESTS_CA_BUNDLE = ''

# Navigate to memOS directory
Set-Location -Path "$PSScriptRoot\..\memOS"

Write-Host "Reinstalling memOS package in editable mode..." -ForegroundColor Yellow
poetry install

if ($LASTEXITCODE -eq 0) {
    Write-Host "memOS installation fixed successfully!" -ForegroundColor Green
    
    # Verify installation
    Write-Host "`nVerifying memos_mcp package..." -ForegroundColor Cyan
    poetry run pip show memos-mcp
    
} else {
    Write-Host "Installation failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}
