<#
.SYNOPSIS
    End-to-End Testing Script for Soma Ecosystem
    
.DESCRIPTION
    Validates that all services are running correctly and connected to Cortex dashboard.
    Tests health endpoints, telemetry streams, and service integrations.
    
.EXAMPLE
    .\test_ecosystem.ps1
    
.EXAMPLE
    .\test_ecosystem.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Continue'
$Script:TestResults = @()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = '',
        [string]$Details = ''
    )
    
    $Result = [PSCustomObject]@{
        Test = $TestName
        Status = if ($Passed) { 'PASS' } else { 'FAIL' }
        Message = $Message
        Details = $Details
        Timestamp = Get-Date
    }
    
    $Script:TestResults += $Result
    
    $Symbol = if ($Passed) { '✓' } else { '✗' }
    $Color = if ($Passed) { 'Green' } else { 'Red' }
    
    Write-Host "  $Symbol " -ForegroundColor $Color -NoNewline
    Write-Host "$TestName" -ForegroundColor White
    
    if ($Message) {
        Write-Host "    $Message" -ForegroundColor Gray
    }
    
    if ($Details -and $VerbosePreference -eq 'Continue') {
        Write-Host "    Details: $Details" -ForegroundColor DarkGray
    }
}

function Test-HttpEndpoint {
    param(
        [string]$Url,
        [string]$ExpectedContent = '',
        [int]$TimeoutSec = 10
    )
    
    try {
        $Response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        
        if ($Response.StatusCode -eq 200) {
            if ($ExpectedContent) {
                return $Response.Content -like "*$ExpectedContent*"
            }
            return $true
        }
        return $false
    }
    catch {
        Write-Verbose "HTTP request failed: $_"
        return $false
    }
}

# ============================================================================
# TEST SUITES
# ============================================================================

function Test-DockerInfrastructure {
    Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         TEST SUITE: Docker Infrastructure                 ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    # Test PostgreSQL
    try {
        $PgTest = Test-NetConnection -ComputerName localhost -Port 6000 -InformationLevel Quiet -WarningAction SilentlyContinue
        Write-TestResult -TestName "PostgreSQL (Port 6000)" -Passed $PgTest -Message $(if ($PgTest) { "Accepting connections" } else { "Not reachable" })
    }
    catch {
        Write-TestResult -TestName "PostgreSQL (Port 6000)" -Passed $false -Message "Connection test failed"
    }
    
    # Test Neo4j
    try {
        $Neo4jTest = Test-NetConnection -ComputerName localhost -Port 7687 -InformationLevel Quiet -WarningAction SilentlyContinue
        Write-TestResult -TestName "Neo4j Bolt (Port 7687)" -Passed $Neo4jTest -Message $(if ($Neo4jTest) { "Accepting connections" } else { "Not reachable" })
    }
    catch {
        Write-TestResult -TestName "Neo4j Bolt (Port 7687)" -Passed $false -Message "Connection test failed"
    }
    
    # Test Neo4j Browser
    $Neo4jBrowser = Test-HttpEndpoint -Url "http://localhost:7474" -TimeoutSec 5
    Write-TestResult -TestName "Neo4j Browser (Port 7474)" -Passed $Neo4jBrowser -Message $(if ($Neo4jBrowser) { "Web interface available" } else { "Not accessible" })
    
    # Test Redis
    try {
        $RedisTest = Test-NetConnection -ComputerName localhost -Port 6380 -InformationLevel Quiet -WarningAction SilentlyContinue
        Write-TestResult -TestName "Redis (Port 6380)" -Passed $RedisTest -Message $(if ($RedisTest) { "Accepting connections" } else { "Not reachable" })
    }
    catch {
        Write-TestResult -TestName "Redis (Port 6380)" -Passed $false -Message "Connection test failed"
    }
}

function Test-PythonServices {
    Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         TEST SUITE: Python Services                       ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    $Services = @(
        @{ Name = "InGress"; Port = 8000; Path = "/health" }
        @{ Name = "InGest"; Port = 8766; Path = "/health" }
        @{ Name = "OmegaKG"; Port = 8765; Path = "/health" }
        @{ Name = "memOS"; Port = 8768; Path = "/health" }
    )
    
    foreach ($Service in $Services) {
        $HealthUrl = "http://localhost:$($Service.Port)$($Service.Path)"
        $Passed = Test-HttpEndpoint -Url $HealthUrl -TimeoutSec 5
        
        if ($Passed) {
            # Try to get health details
            try {
                $Response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5 -ErrorAction Stop
                $Message = "Status: $($Response.status)"
                if ($Response.version) {
                    $Message += " | Version: $($Response.version)"
                }
                Write-TestResult -TestName "$($Service.Name) Health" -Passed $true -Message $Message
            }
            catch {
                Write-TestResult -TestName "$($Service.Name) Health" -Passed $true -Message "Endpoint responding"
            }
        }
        else {
            Write-TestResult -TestName "$($Service.Name) Health" -Passed $false -Message "Health endpoint not responding"
        }
        
        # Test API docs
        $DocsUrl = "http://localhost:$($Service.Port)/docs"
        $DocsAvailable = Test-HttpEndpoint -Url $DocsUrl -TimeoutSec 3
        Write-TestResult -TestName "$($Service.Name) API Docs" -Passed $DocsAvailable -Message $(if ($DocsAvailable) { "Available at /docs" } else { "Not accessible" })
    }
}

function Test-CortexDashboard {
    Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         TEST SUITE: Cortex Dashboard                      ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    # Test main page
    $MainPage = Test-HttpEndpoint -Url "http://localhost:5173" -TimeoutSec 10
    Write-TestResult -TestName "Cortex Main Page" -Passed $MainPage -Message $(if ($MainPage) { "Dashboard accessible" } else { "Not responding" })
    
    # Test if Vite dev server is running
    if ($MainPage) {
        try {
            $Response = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 5 -UseBasicParsing
            $IsVite = $Response.Content -like "*vite*" -or $Response.Content -like "*React*"
            Write-TestResult -TestName "Vite Dev Server" -Passed $IsVite -Message $(if ($IsVite) { "Running with HMR" } else { "Static content" })
        }
        catch {
            Write-TestResult -TestName "Vite Dev Server" -Passed $false -Message "Could not verify"
        }
    }
}

function Test-ServiceIntegration {
    Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         TEST SUITE: Service Integration                   ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    # Test InGress telemetry stream
    try {
        $IngressStream = Test-HttpEndpoint -Url "http://localhost:8000/api/v1/telemetry/stream" -TimeoutSec 3
        Write-TestResult -TestName "InGress Telemetry Stream" -Passed $IngressStream -Message $(if ($IngressStream) { "SSE endpoint available" } else { "Not accessible" })
    }
    catch {
        Write-TestResult -TestName "InGress Telemetry Stream" -Passed $false -Message "Stream endpoint failed"
    }
    
    # Test memOS pulse stream
    try {
        $PulseStream = Test-HttpEndpoint -Url "http://localhost:8768/pulse/stream" -TimeoutSec 3
        Write-TestResult -TestName "memOS Pulse Stream" -Passed $PulseStream -Message $(if ($PulseStream) { "SSE endpoint available" } else { "Not accessible" })
    }
    catch {
        Write-TestResult -TestName "memOS Pulse Stream" -Passed $false -Message "Stream endpoint failed"
    }
    
    # Test OmegaKG capture endpoint
    try {
        $CaptureEndpoint = Test-HttpEndpoint -Url "http://localhost:8765/api/v1/capture/recent" -TimeoutSec 5
        Write-TestResult -TestName "OmegaKG Capture API" -Passed $CaptureEndpoint -Message $(if ($CaptureEndpoint) { "Capture endpoint responding" } else { "Not accessible" })
    }
    catch {
        Write-TestResult -TestName "OmegaKG Capture API" -Passed $false -Message "Endpoint failed"
    }
    
    # Test InGest vitals endpoint
    try {
        $Vitals = Test-HttpEndpoint -Url "http://localhost:8766/api/v1/vitals" -TimeoutSec 5
        Write-TestResult -TestName "InGest Vitals API" -Passed $Vitals -Message $(if ($Vitals) { "Vitals endpoint responding" } else { "Not accessible" })
    }
    catch {
        Write-TestResult -TestName "InGest Vitals API" -Passed $false -Message "Endpoint failed"
    }
}

function Test-EndToEndFlow {
    Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         TEST SUITE: End-to-End Flow                       ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    Write-Host "  ℹ  Checking for trace-meal.ps1 script..." -ForegroundColor Blue
    
    $TraceMealScript = Join-Path $PSScriptRoot "scripts\operations\trace-meal.ps1"
    if (Test-Path $TraceMealScript) {
        try {
            Write-Host "  ⚡ Running meal trace test..." -ForegroundColor Yellow
            $TraceOutput = & $TraceMealScript 2>&1
            $TraceSuccess = $LASTEXITCODE -eq 0
            
            Write-TestResult -TestName "Meal Trace Test" -Passed $TraceSuccess -Message $(if ($TraceSuccess) { "Complete flow verified" } else { "Flow test failed" }) -Details "$TraceOutput"
        }
        catch {
            Write-TestResult -TestName "Meal Trace Test" -Passed $false -Message "Script execution failed: $_"
        }
    }
    else {
        Write-Host "  ⚠  trace-meal.ps1 not found, skipping E2E test" -ForegroundColor Yellow
    }
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

Write-Host "`n╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║                  SOMA ECOSYSTEM TEST SUITE                            ║" -ForegroundColor Magenta
Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta

$StartTime = Get-Date

# Run all test suites
Test-DockerInfrastructure
Test-PythonServices
Test-CortexDashboard
Test-ServiceIntegration
Test-EndToEndFlow

# Generate summary
$EndTime = Get-Date
$Duration = ($EndTime - $StartTime).TotalSeconds

Write-Host "`n╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                         TEST SUMMARY                                  ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

$TotalTests = $Script:TestResults.Count
$PassedTests = ($Script:TestResults | Where-Object { $_.Status -eq 'PASS' }).Count
$FailedTests = ($Script:TestResults | Where-Object { $_.Status -eq 'FAIL' }).Count
$SuccessRate = if ($TotalTests -gt 0) { [math]::Round(($PassedTests / $TotalTests) * 100, 1) } else { 0 }

Write-Host "`nTotal Tests: $TotalTests" -ForegroundColor White
Write-Host "Passed: $PassedTests" -ForegroundColor Green
Write-Host "Failed: $FailedTests" -ForegroundColor $(if ($FailedTests -gt 0) { 'Red' } else { 'Gray' })
Write-Host "Success Rate: $SuccessRate%" -ForegroundColor $(if ($SuccessRate -ge 90) { 'Green' } elseif ($SuccessRate -ge 70) { 'Yellow' } else { 'Red' })
Write-Host "Duration: $([math]::Round($Duration, 2)) seconds" -ForegroundColor White

if ($FailedTests -gt 0) {
    Write-Host "`n⚠  Failed Tests:" -ForegroundColor Yellow
    foreach ($Failed in ($Script:TestResults | Where-Object { $_.Status -eq 'FAIL' })) {
        Write-Host "  - $($Failed.Test): $($Failed.Message)" -ForegroundColor Red
    }
}

# Export results to JSON
$ResultsFile = Join-Path $PSScriptRoot "logs\test_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$Script:TestResults | ConvertTo-Json -Depth 3 | Out-File $ResultsFile -Encoding UTF8
Write-Host "`nDetailed results saved to: $ResultsFile" -ForegroundColor Gray

# Exit with appropriate code
if ($FailedTests -gt 0) {
    Write-Host "`n❌ SOME TESTS FAILED - Review logs for details" -ForegroundColor Red
    exit 1
}
else {
    Write-Host "`n✅ ALL TESTS PASSED - Ecosystem is healthy!" -ForegroundColor Green
    exit 0
}
