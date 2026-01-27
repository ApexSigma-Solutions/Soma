#!/usr/bin/env pwsh
<#
.SYNOPSIS
    MVP-001 Phase 2 Launch Verification - Multi-Environment Audit Runner

.DESCRIPTION
    Orchestrates comprehensive verification across all three OmegaKG environments:
    - Dev: Full testing (ephemeral data)
    - Temp: Full testing (ephemeral data)
    - Stable: Conservative testing (persistent production data)

.PARAMETER Environment
    Target environment: dev, stable, or temp

.PARAMETER Mode
    Verification mode: static, live, full, or conservative

.PARAMETER SkipDatabase
    Skip database-dependent tests (Neo4j, PostgreSQL)

.PARAMETER Diagnostic
    Enable diagnostic mode with detailed error traces

.PARAMETER Verbose
    Enable verbose output

.EXAMPLE
    .\run_phase2_audit.ps1 -Environment dev

.EXAMPLE
    .\run_phase2_audit.ps1 -Environment stable -Mode conservative
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("dev", "stable", "temp")]
    [string]$Environment,

    [Parameter()]
    [ValidateSet("static", "live", "full", "conservative")]
    [string]$Mode = "full",

    [Parameter()]
    [switch]$SkipDatabase,

    [Parameter()]
    [switch]$Diagnostic,

    [Parameter()]
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Color codes for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Cyan = "Cyan"
    White = "White"
    Magenta = "Magenta"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = $Colors.White
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Text)
    Write-ColorOutput "`n$('=' * 80)" $Colors.Cyan
    Write-ColorOutput $Text $Colors.Cyan
    Write-ColorOutput "$('=' * 80)`n" $Colors.Cyan
}

function Test-VirtualEnvironment {
    """Check if Python virtual environment exists and is activated"""
    $python = ".venv\Scripts\python.exe"

    if (-not (Test-Path $python)) {
        # Try alternative location
        $python = "python.exe"
        try {
            $null = & $python --version
        } catch {
            Write-ColorOutput "[ERROR] Python virtual environment not found!" $Colors.Red
            Write-ColorOutput "Please run: .venv\Scripts\Activate.ps1" $Colors.Yellow
            return $false
        }
    }

    Write-ColorOutput "[OK] Python executable found" $Colors.Green
    return $true
}

function Test-OmegaKGEnvironment {
    """Check if we're in an OmegaKG environment directory"""
    # Check for pyproject.toml
    if (-not (Test-Path "pyproject.toml")) {
        Write-ColorOutput "[ERROR] pyproject.toml not found!" $Colors.Red
        Write-ColorOutput "Please run this script from an OmegaKG environment directory" $Colors.Yellow
        Write-ColorOutput "  Example: cd D:\projects\OmegaKG\Omega_KG_dev" $Colors.Yellow
        return $false
    }

    Write-ColorOutput "[OK] OmegaKG environment detected" $Colors.Green
    return $true
}

function Get-EnvironmentInfo {
    """Get environment-specific information"""
    $envInfo = @{
        Name = $Environment
        VaultPath = $null
        Neo4jPort = $null
        PostgresPort = $null
        RiskLevel = $null
    }

    switch ($Environment) {
        "dev" {
            $envInfo.VaultPath = "./vault"
            $envInfo.Neo4jPort = "7688"
            $envInfo.PostgresPort = "5433"
            $envInfo.RiskLevel = "LOW (ephemeral data)"
        }
        "temp" {
            $envInfo.VaultPath = "./vault"
            $envInfo.Neo4jPort = "7689"
            $envInfo.PostgresPort = "5433"
            $envInfo.RiskLevel = "LOW (ephemeral data)"
        }
        "stable" {
            # Stable uses external vault path
            $envInfo.VaultPath = "D:/projects/omegavault.as"
            $envInfo.Neo4jPort = "7687"
            $envInfo.PostgresPort = "5800"
            $envInfo.RiskLevel = "HIGH (production data)"
        }
    }

    return $envInfo
}

function Start-DatabaseServices {
    """Start database services if needed"""
    Write-ColorOutput "`nChecking database services..." $Colors.Yellow

    # Determine docker-compose file
    $composeFile = "docker-compose.yml"

    # Check if Neo4j is running
    $neo4jRunning = $false
    try {
        $result = docker ps --filter "publish=$($envInfo.Neo4jPort)" --format "{{.Names}}" | Select-String "neo4j"
        if ($result) {
            $neo4jRunning = $true
            Write-ColorOutput "[OK] Neo4j service is running" $Colors.Green
        }
    } catch {
        Write-ColorOutput "[WARNING] Could not check Neo4j status" $Colors.Yellow
    }

    if (-not $neo4jRunning) {
        Write-ColorOutput "[INFO] Starting Neo4j service..." $Colors.Yellow
        try {
            docker-compose -f $composeFile up -d neo4j
            Write-ColorOutput "[OK] Neo4j service started" $Colors.Green
        } catch {
            Write-ColorOutput "[WARNING] Could not start Neo4j: $_" $Colors.Yellow
            Write-ColorOutput "         Some tests may be skipped" $Colors.Yellow
        }
    }

    # Check if PostgreSQL is running
    $postgresRunning = $false
    try {
        $result = docker ps --filter "publish=$($envInfo.PostgresPort)" --format "{{.Names}}" | Select-String "postgres"
        if ($result) {
            $postgresRunning = $true
            Write-ColorOutput "[OK] PostgreSQL service is running" $Colors.Green
        }
    } catch {
        Write-ColorOutput "[WARNING] Could not check PostgreSQL status" $Colors.Yellow
    }

    if (-not $postgresRunning) {
        Write-ColorOutput "[INFO] Starting PostgreSQL service..." $Colors.Yellow
        try {
            docker-compose -f $composeFile up -d postgres
            Write-ColorOutput "[OK] PostgreSQL service started" $Colors.Green
        } catch {
            Write-ColorOutput "[WARNING] Could not start PostgreSQL: $_" $Colors.Yellow
            Write-ColorOutput "           Some tests may be skipped" $Colors.Yellow
        }
    }
}

function Invoke-Phase2Audit {
    """Execute the Phase 2 audit"""
    param($Environment, $Mode, $SkipDatabase, $Diagnostic)

    # Build command arguments
    $script = "scripts\verify_phase2_readiness.py"
    $args = @("--environment", $Environment, "--mode", $Mode)

    if ($SkipDatabase) {
        $args += "--skip-database"
    }

    if ($Diagnostic) {
        $args += "--diagnostic"
    }

    if ($Verbose) {
        $args += "--verbose"
    }

    Write-ColorOutput "`nExecuting Phase 2 verification..." $Colors.Yellow
    Write-ColorOut "Command: python $script $($args -join ' ')" $Colors.Cyan

    # Execute the Python script
    try {
        & python $script @args
        $exitCode = $LASTEXITCODE
        return $exitCode
    } catch {
        Write-ColorOutput "[ERROR] Failed to execute verification script: $_" $Colors.Red
        return 1
    }
}

function Show-EnvironmentWarning {
    """Show environment-specific warnings"""
    if ($Environment -eq "stable") {
        Write-ColorOutput "`n" $Colors.White
        Write-ColorOut "⚠️  WARNING: STABLE ENVIRONMENT ⚠️" $Colors.Magenta
        Write-ColorOut "You are running the audit on the STABLE (production) environment." $Colors.Magenta
        Write-ColorOut "This environment uses PERSISTENT VOLUMES and contains PRODUCTION DATA." $Colors.Magenta
        Write-ColorOut "Please ensure you have a backup before proceeding." $Colors.Magenta
        Write-ColorOut "`nPress Ctrl+C to cancel, or wait 5 seconds to continue..." $Colors.Yellow

        try {
            Start-Sleep -Seconds 5
        } catch {
            Write-ColorOutput "`nAudit cancelled by user" $Colors.Yellow
            exit 130
        }
    }
}

function Show-Results {
    """Display audit results"""
    param($ExitCode)

    Write-Header "AUDIT RESULTS"

    switch ($ExitCode) {
        0 {
            Write-ColorOutput "✅ SUCCESS: Phase 2 verification PASSED" $Colors.Green
            Write-ColorOutput "All systems are ready for Phase 2 launch!" $Colors.Green
        }
        1 {
            Write-ColorOutput "❌ FAILURE: Phase 2 verification FAILED" $Colors.Red
            Write-ColorOutput "Critical issues found. Please review the errors above." $Colors.Red
        }
        2 {
            Write-ColorOutput "⚠️  PARTIAL SUCCESS: Some tests were skipped" $Colors.Yellow
            Write-ColorOutput "This is acceptable if services are unavailable." $Colors.Yellow
            Write-ColorOutput "Review the detailed report for more information." $Colors.Yellow
        }
        130 {
            Write-ColorOutput "⚠️  AUDIT CANCELLED" $Colors.Yellow
            exit 130
        }
        default {
            Write-ColorOutput "❓ UNKNOWN: Unexpected exit code: $ExitCode" $Colors.Red
        }
    }

    # Show report location
    $reportFiles = Get-ChildItem -Path "reports" -Filter "phase2_audit_${Environment}_*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending

    if ($reportFiles) {
        Write-ColorOutput "`nDetailed reports available at:" $Colors.Cyan
        foreach ($report in $reportFiles | Select-Object -First 3) {
            Write-ColorOutput "  - $($report.FullName)" $Colors.White
        }
    }

    Write-ColorOutput "`n" + ("=" * 80) $Colors.Cyan
}

# Main Execution
try {
    Write-Header "MVP-001 Phase 2 Launch Verification"

    # Get environment information
    $envInfo = Get-EnvironmentInfo

    # Display environment details
    Write-ColorOutput "Environment: $Environment" $Colors.Cyan
    Write-ColorOutput "Mode: $Mode" $Colors.Cyan
    Write-ColorOutput "Vault Path: $($envInfo.VaultPath)" $Colors.Cyan
    Write-ColorOutput "Neo4j Port: $($envInfo.Neo4jPort)" $Colors.Cyan
    Write-ColorOutput "PostgreSQL Port: $($envInfo.PostgresPort)" $Colors.Cyan
    Write-ColorOutput "Risk Level: $($envInfo.RiskLevel)" $Colors.Cyan
    Write-ColorOutput "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" $Colors.Cyan

    # Environment-specific warnings
    Show-EnvironmentWarning

    # Pre-flight checks
    Write-Header "Pre-Flight Checks"

    if (-not (Test-VirtualEnvironment)) {
        exit 1
    }

    if (-not (Test-OmegaKGEnvironment)) {
        exit 1
    }

    # Start database services if not skipped
    if (-not $SkipDatabase) {
        Start-DatabaseServices
    }

    # Run the audit
    $exitCode = Invoke-Phase2Audit -Environment $Environment -Mode $Mode -SkipDatabase:$SkipDatabase -Diagnostic:$Diagnostic

    # Show results
    Show-Results -ExitCode $exitCode

    # Exit with the same code as the audit
    exit $exitCode

} catch {
    Write-ColorOutput "`n[ERROR] Unexpected error: $_" $Colors.Red
    if ($Diagnostic -or $Verbose) {
        Write-ColorOutput "`nStack Trace:" $Colors.Red
        Write-ColorOutput $_.ScriptStackTrace $Colors.Red
    }
    exit 1
}
