$baseUrl = "http://127.0.0.1:8002"
$apiKey = "change_me_secure_api_key"

# 1. Health
Write-Host "Checking Health..."
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    if ($health.status -ne "healthy") { 
        Write-Error "Unhealthy: $($health | ConvertTo-Json)"
        exit 1 
    }
    Write-Host "Healthy!"
} catch {
    Write-Error "Health Check Failed. Is server running? Error: $_"
    exit 1
}

# 2. Auth
Write-Host "Authenticating..."
try {
    $tokenResp = Invoke-RestMethod -Uri "$baseUrl/auth/token" -Method Post -Headers @{ "X-API-Key" = $apiKey }
    $token = $tokenResp.access_token
    Write-Host "Got Token: $($token.Substring(0, 10))..."
} catch {
    Write-Error "Auth Failed. Check API Key. Error: $_"
    exit 1
}

# 3. Capture
Write-Host "Sending Capture..."
$body = @{
    platform = "TestPlatform"
    url = "http://example.com"
    messages = @(
        @{ role = "user"; content = "Hello" }
        @{ role = "assistant"; content = "I decided to answer." }
    )
} | ConvertTo-Json -Depth 5

try {
    $capResp = Invoke-RestMethod -Uri "$baseUrl/capture" -Method Post -Headers @{ "Authorization" = "Bearer $token"; "Content-Type"="application/json" } -Body $body
    Write-Host "Capture Result: $($capResp.success)"
    Write-Host "Nodes: $($capResp.nodes_created)"
    if (-not $capResp.success) { exit 1 }
} catch {
    Write-Error "Capture Failed: $_"
    exit 1
}
