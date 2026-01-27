#!/usr/bin/env pwsh
# Security Verification Script
# Checks for sensitive files and patterns in the repository

param(
    [switch]$SkipGitHistory = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Security Verification Script" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Track if any issues found
$global:IssuesFound = $false

# Function to print results
function Print-Result {
    param(
        [int]$Result,
        [string]$Message
    )

    if ($Result -eq 0) {
        Write-Host "✓ PASS: $Message" -ForegroundColor Green
    } else {
        Write-Host "✗ FAIL: $Message" -ForegroundColor Red
        $global:IssuesFound = $true
    }
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ WARNING: $Message" -ForegroundColor Yellow
}

Write-Host "1. Checking for private key files..." -ForegroundColor White

$privateKeyPatterns = @(
    "*.pem", "*.key", "*.crt", "*.p12", "*.pfx", "*.jks",
    "*_rsa", "*_dsa", "*_ecdsa", "*_ed25519", "id_rsa*", "*.priv"
)

$privateKeys = Get-ChildItem -Path . -File -Recurse -Include $privateKeyPatterns -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "*.git*" }

if ($privateKeys.Count -eq 0) {
    Print-Result 0 "No private key files found"
} else {
    Print-Result 1 "Private key files found:"
    $privateKeys | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor Red }
}
Write-Host ""

Write-Host "2. Checking for .env files (excluding examples)..." -ForegroundColor White
$envFiles = Get-ChildItem -Path . -File -Name ".env" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_ -notlike "*.git*" }

if ($envFiles.Count -eq 0) {
    Print-Result 0 "No .env files found in repository"
} else {
    Print-Warning ".env files should not be committed:"
    $envFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    Write-Host ""
}
Write-Host ""

Write-Host "3. Checking .gitignore for security patterns..." -ForegroundColor White
$requiredPatterns = @("*.pem", "*.key", ".env")

if (Test-Path ".gitignore") {
    $gitignore = Get-Content ".gitignore" -Raw
    $missingPatterns = @()

    foreach ($pattern in $requiredPatterns) {
        if ($gitignore -notmatch [regex]::Escape($pattern)) {
            $missingPatterns += $pattern
        }
    }

    if ($missingPatterns.Count -eq 0) {
        Print-Result 0 "Required .gitignore patterns present"
    } else {
        Print-Result 1 "Missing .gitignore patterns: $($missingPatterns -join ', ')"
    }
} else {
    Print-Result 1 "No .gitignore found"
}
Write-Host ""

Write-Host "4. Checking git history for sensitive files..." -ForegroundColor White

if (-not $SkipGitHistory) {
    try {
        $historyCheck = git log --all --full-history --oneline -- "*.pem", "*.key" 2>$null | Select-Object -First 5

        if ([string]::IsNullOrEmpty($historyCheck)) {
            Print-Result 0 "No sensitive files found in git history"
        } else {
            Print-Result 1 "Sensitive files found in git history:"
            Write-Host $historyCheck -ForegroundColor Red
            Write-Host ""
            Write-Host "Run: git log --all --full-history -- *.pem" -ForegroundColor Yellow
        }
    } catch {
        Print-Warning "Could not check git history (not a git repository or git not installed)"
    }
} else {
    Write-Host "Skipped (--SkipGitHistory specified)" -ForegroundColor Gray
}
Write-Host ""

Write-Host "5. Checking for hardcoded API keys..." -ForegroundColor White

# Common API key patterns
$apiKeyPatterns = @(
    @{ Name="OpenAI"; Pattern="sk-[a-zA-Z0-9]{20,}" },
    @{ Name="Google"; Pattern="AIza[a-zA-Z0-9_-]{35}" },
    @{ Name="AWS"; Pattern="AKIA[a-zA-Z0-9]{16}" },
    @{ Name="GitHub"; Pattern="ghp_[a-zA-Z0-9]{36}" }
)

$foundKeys = $false
foreach ($apiPattern in $apiKeyPatterns) {
    $matches = Get-ChildItem -Path . -File -Recurse -Include "*.py", "*.js", "*.ts", "*.json" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike "*.git*" -and $_.FullName -notlike "*node_modules*" } |
        ForEach-Object {
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -match $apiPattern.Pattern) {
                $_
            }
        }

    if ($matches.Count -gt 0) {
        $foundKeys = $true
        Print-Result 1 "$($apiPattern.Name) API keys detected:"
        $matches | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor Red }
    }
}

if (-not $foundKeys) {
    Print-Result 0 "No hardcoded API keys detected"
}
Write-Host ""

Write-Host "6. Checking pre-commit hooks..." -ForegroundColor White

if (Test-Path ".pre-commit-config.yaml") {
    $precommit = Get-Content ".pre-commit-config.yaml" -Raw
    if ($precommit -match "detect-private-key") {
        Print-Result 0 "Pre-commit detect-private-key hook configured"
    } else {
        Print-Result 1 "Pre-commit detect-private-key hook not configured"
    }
} else {
    Print-Result 1 "No .pre-commit-config.yaml found"
}
Write-Host ""

Write-Host "7. Checking security documentation..." -ForegroundColor White
$securityDocs = @("SECURITY.md", "docs\SECURITY_INCIDENT_PEM.md", "docs\SECURITY_RUNBOOK.md")
$missingDocs = @()

foreach ($doc in $securityDocs) {
    if (-not (Test-Path $doc)) {
        $missingDocs += $doc
    }
}

if ($missingDocs.Count -eq 0) {
    Print-Result 0 "All security documentation present"
} else {
    Print-Result 1 "Missing security documentation: $($missingDocs -join ', ')"
}
Write-Host ""

Write-Host "8. Checking for large files (>1MB)..." -ForegroundColor White

$largeFiles = Get-ChildItem -Path . -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Length -gt 1MB -and
        $_.FullName -notlike "*.git*" -and
        $_.FullName -notlike "*node_modules*" -and
        $_.FullName -notlike "*.venv*"
    }

if ($largeFiles.Count -eq 0) {
    Print-Result 0 "No unusually large files found"
} else {
    Print-Warning "Large files found (review if they should be in git):"
    $largeFiles | ForEach-Object {
        $size = if ($_.Length -gt 1MB) { "{0:N2} MB" -f ($_.Length / 1MB) } else { "{0:N2} KB" -f ($_.Length / 1KB) }
        Write-Host "  $size - $($_.FullName)" -ForegroundColor Yellow
    }
}
Write-Host ""

Write-Host "9. Checking for secrets in environment variables..." -ForegroundColor White

# Check for suspicious environment variable patterns
$suspiciousEnvVars = @(
    "SECRET", "PASSWORD", "API_KEY", "TOKEN", "PRIVATE_KEY", "ACCESS_KEY"
)

$foundEnvIssues = $false
foreach ($varName in $suspiciousEnvVars) {
    $envVar = [Environment]::GetEnvironmentVariable($varName)
    if ($envVar) {
        $foundEnvIssues = $true
        Print-Warning "Environment variable $varName is set (verify it's not exposed)"
    }
}

if (-not $foundEnvIssues) {
    Print-Result 0 "No suspicious environment variables found"
}
Write-Host ""

Write-Host "10. Checking file permissions on sensitive files..." -ForegroundColor White

$sensitiveFiles = @(".env", "*.pem", "*.key")
$permissionIssues = $false

foreach ($pattern in $sensitiveFiles) {
    $files = Get-ChildItem -Path . -File -Include $pattern -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike "*.git*" }

    foreach ($file in $files) {
        $acl = Get-Acl $file.FullName
        $worldWritable = $acl.Access | Where-Object {
            $_.IdentityReference -eq "Everyone" -or
            $_.IdentityReference -eq "NT AUTHORITY\Everyone"
        }

        if ($worldWritable) {
            $permissionIssues = $true
            Print-Warning "World-writable file: $($file.FullName)"
        }
    }
}

if (-not $permissionIssues) {
    Print-Result 0 "No permission issues on sensitive files"
}
Write-Host ""

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Security Verification Complete" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

if ($global:IssuesFound) {
    Write-Host "Security issues found. Please review and fix." -ForegroundColor Red
    Write-Host ""
    Write-Host "See SECURITY.md for security best practices." -ForegroundColor Yellow
    Write-Host "See docs\SECURITY_RUNBOOK.md for remediation steps." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "All security checks passed!" -ForegroundColor Green
    exit 0
}
