<#
.SYNOPSIS
    Backup Neo4j Docker named volume and restart docker-compose stack safely.

.DESCRIPTION
    Creates a timestamped tar.gz of the named Docker volume `apexsigma.neo4j.data`
    into a `docker_backups` directory in the project. Then brings the compose
    stack down and back up. Includes checks for Docker and Poetry availability.

.PARAMETER DryRun
    When supplied, the script will NOT perform docker stop/start or volume
    backup operations. It will still perform Poetry checks so you can verify
    dependency state without impacting running services.

.EXAMPLE
    .\backup-and-restart.ps1

.EXAMPLE
    .\backup-and-restart.ps1 -DryRun
#>

param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest

function Write-Info { param($m) Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Warn { param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red }

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$backupDir = Join-Path $projectRoot 'docker_backups'

Write-Info "Project root: $projectRoot"
Write-Info "Backup directory: $backupDir"

if (-not (Test-Path $backupDir)) {
    if ($DryRun) { Write-Info "(DryRun) Would create backup dir: $backupDir" } else { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }
}

# Check Docker
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Err "Docker CLI not found in PATH. Please install Docker Desktop or add docker to PATH."; exit 2
}

# Check Poetry availability (we'll still run checks in DryRun)
$poetryCmd = Get-Command poetry -ErrorAction SilentlyContinue
if (-not $poetryCmd) {
    Write-Warn "Poetry not found in PATH. Poetry checks will be skipped. Install from https://python-poetry.org/docs/"
} else {
    try {
        $poetryVersion = (& poetry --version) -join " `n"
        Write-Info "Poetry version: $poetryVersion"
    } catch {
        Write-Warn "Failed to run 'poetry --version' but Poetry command exists. Continuing. Error: $_"
    }
}

# Function: create backup of named volume
function Backup-Neo4jVolume {
    param(
        [string]$NamedVolume = 'apexsigma.neo4j.data'
    )

    # Retention policy: keep only the last 7 backups
    try {
        $existingBackups = Get-ChildItem -Path $backupDir -Filter "neo4j_backup_*.tar.gz" -File -ErrorAction SilentlyContinue |
                           Sort-Object LastWriteTime -Descending
        if ($existingBackups -and $existingBackups.Count -gt 7) {
            $toDelete = $existingBackups | Select-Object -Skip 7
            foreach ($item in $toDelete) {
                Write-Info "Removing old backup: $($item.FullName)"
                if ($DryRun) {
                    Write-Info "(DryRun) Would remove: $($item.FullName)"
                } else {
                    try {
                        Remove-Item -LiteralPath $item.FullName -Force -ErrorAction Stop
                    } catch {
                        Write-Err "Failed to remove old backup '$($item.FullName)': $_"
                        continue
                    }
                }
            }
        }
    } catch {
        Write-Err "Retention policy encountered an error: $_"
        throw
    }
}

# Call the backup function outside its definition
try {
    if (-not $DryRun) {
        $null = Backup-Neo4jVolume
    } else {
        Write-Info "DryRun: skipping actual volume backup, but running poetry checks."
    $tarCmd = "tar czf /backup/$archiveName ."
    if ($DryRun) {
        Write-Info "(DryRun) Would run: docker run --rm -v ${NamedVolume}:/data -v `"$backupDir`":/backup alpine sh -c 'cd /data && $tarCmd'"
    } else {
        Write-Info "Running backup: docker run --rm -v ${NamedVolume}:/data -v `"$backupDir`":/backup alpine sh -c 'cd /data && $tarCmd'"
        docker run --rm -v ${NamedVolume}:/data -v "$backupDir":/backup alpine sh -c "cd /data && $tarCmd"
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Backup command failed with exit code $LASTEXITCODE"
            throw "Backup failed"
        }
    }

    Restart-ComposeStack

    Write-Info "Collecting some logs for verification (last 80 lines)"
    if (-not $DryRun) {
        docker compose logs --tail 80 neo4j-db | Out-Host
        docker compose logs --tail 80 omega-kg | Out-Host
    } else {
        Write-Info "(DryRun) Skipping container logs collection"
    }

    # Poetry dependency checks
    if ($poetryCmd) {
        Write-Info "Running 'poetry install' to ensure dependencies are available (may modify virtualenv)"
        try {
            # Run poetry install in project root
            Push-Location $projectRoot
            if ($DryRun) {
                Write-Info "(DryRun) Would run: poetry install"
            } else {
                poetry install
            }

            Write-Info "Checking for outdated packages (poetry show --outdated)"
            if ($DryRun) {
                Write-Info "(DryRun) Would run: poetry show --outdated"
            } else {
                $outdated = poetry show --outdated
                if ([string]::IsNullOrWhiteSpace($outdated)) { Write-Info "All packages up-to-date according to Poetry." } else { Write-Info "Outdated packages:\n$outdated" }
            }
        } finally { Pop-Location }
    } else {
        Write-Warn "Poetry not available; skipping dependency installation/outdated check."
    }

    Write-Info "Operation completed."; exit 0

} catch {
    Write-Err "Unhandled exception: $_"; exit 10
}
