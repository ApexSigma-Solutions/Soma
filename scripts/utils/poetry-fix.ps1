<#
.SYNOPSIS
    Fix Poetry SSL/Certificate Issues on Windows

.DESCRIPTION
    PostgreSQL installation on Windows often sets SSL_CERT_FILE or similar
    environment variables that conflict with Poetry's certificate handling.
    
    This script provides a wrapper for Poetry commands that ensures the correct
    certifi certificate bundle is used.

.NOTES
    Author: ApexSigma Solutions
    Date: 2026-02-02
    Issue: Poetry fails with "Could not find suitable TLS CA certificate bundle"
    Root Cause: PostgreSQL sets cert path to non-existent location
    
.EXAMPLE
    .\poetry-fix.ps1 lock
    .\poetry-fix.ps1 install
    .\poetry-fix.ps1 update requests
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$PoetryArgs
)

$ErrorActionPreference = "Stop"

Write-Host "Poetry SSL Certificate Fix Wrapper" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Detect certifi bundle location
try {
    $CertifiPath = poetry run python -c "import certifi; print(certifi.where())" 2>$null
    
    if (-not $CertifiPath) {
        Write-Host "⚠ Warning: Could not find certifi bundle, attempting fallback..." -ForegroundColor Yellow
        # Try without poetry run (use system Python)
        $CertifiPath = python -c "import certifi; print(certifi.where())" 2>$null
    }
    
    if ($CertifiPath -and (Test-Path $CertifiPath)) {
        Write-Host "✓ Using certifi bundle: $CertifiPath" -ForegroundColor Green
        $env:REQUESTS_CA_BUNDLE = $CertifiPath
        $env:SSL_CERT_FILE = $CertifiPath
        $env:CURL_CA_BUNDLE = $CertifiPath
    } else {
        Write-Host "⚠ Warning: Certifi bundle not found, proceeding anyway..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Warning: Could not detect certifi, continuing..." -ForegroundColor Yellow
}

# Run Poetry with proper environment
Write-Host ""
Write-Host "Running: poetry $($PoetryArgs -join ' ')" -ForegroundColor Cyan
Write-Host ""

try {
    & poetry $PoetryArgs
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "✓ Poetry command completed successfully" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "✗ Poetry command failed with exit code: $exitCode" -ForegroundColor Red
    }
    
    exit $exitCode
} catch {
    Write-Host ""
    Write-Host "✗ Error running Poetry: $_" -ForegroundColor Red
    exit 1
}
