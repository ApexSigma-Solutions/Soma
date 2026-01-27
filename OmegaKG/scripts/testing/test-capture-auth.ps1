# CONFIGURATION
$BaseUrl = "http://localhost:8002"
$ApiKey = "test-api-key-for-testing-only"
$UserId = "SigmaDev11"

Write-Host "=== Omega_KG Dev Capture Test (Port 8002) ===" -ForegroundColor Cyan

# STEP 1: Get JWT Token
Write-Host "1. Attempting to authenticate..." -NoNewline
try {
    $AuthResponse = Invoke-RestMethod -Uri "$BaseUrl/auth/token" `
        -Method Post `
        -Headers @{ "x-api-key" = $ApiKey }

    if ($AuthResponse.access_token) {
        $Token = $AuthResponse.access_token
        Write-Host " [SUCCESS]" -ForegroundColor Green
    } else {
        Write-Host " [FAILED] No token returned." -ForegroundColor Red
        exit
    }
}
catch {
    Write-Host " [ERROR]" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit
}

# STEP 2: Send Capture Data
Write-Host "2. Sending Capture Data..." -NoNewline

# UPDATE: Added 'url' and 'platform' which are often required schemas
$Body = @{
    user_id  = $UserId
    content  = "Golden Schema Test: Validating Frontmatter ID and Type."
    source   = "powershell_test_script"
    url      = "http://localhost/test-capture"
    platform = "windows"
} | ConvertTo-Json

try {
    $CaptureResponse = Invoke-RestMethod -Uri "$BaseUrl/capture" `
        -Method Post `
        -Headers @{
            "Authorization" = "Bearer $Token"
            "Content-Type"  = "application/json"
        } `
        -Body $Body

    Write-Host " [SUCCESS]" -ForegroundColor Green
    Write-Host "   Response: $($CaptureResponse | ConvertTo-Json -Depth 2)" -ForegroundColor Yellow
    Write-Host "`n--> CHECK VAULT NOW: Look for the new .md file." -ForegroundColor Cyan
}
catch {
    Write-Host " [ERROR]" -ForegroundColor Red

    # FIXED: PowerShell Core / .NET error reading
    if ($_.Exception.Response -and $_.Exception.Response.Content) {
        $ErrorBody = $_.Exception.Response.Content.ReadAsStringAsync().Result
        Write-Host "   Server Validation Error: $ErrorBody" -ForegroundColor Yellow
    } else {
        Write-Host "   $($_.Exception.Message)"
    }
}
