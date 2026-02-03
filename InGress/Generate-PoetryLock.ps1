# Temporarily clear SSL_CERT_FILE to fix certifi path issue
$originalSSL = $env:SSL_CERT_FILE
$env:SSL_CERT_FILE = $null

try {
    Write-Host "Generating poetry.lock with clean SSL environment..."
    & poetry lock
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "Successfully generated poetry.lock" -ForegroundColor Green
    } else {
        Write-Host "poetry lock failed with exit code: $exitCode" -ForegroundColor Red
        exit $exitCode
    }
} finally {
    # Restore original SSL_CERT_FILE
    $env:SSL_CERT_FILE = $originalSSL
}
