<#
.SYNOPSIS
    Executes TN-OA-009 (ALPHA-91): Documentation Sanitization.
    Removes documentation related to the purged Observability Stack.

.DESCRIPTION
    1. Archives deprecated docs to .archive/docs/
    2. Removes stale observability references.
    3. Updates the BUILD.md (if present) or creates a placeholder.
#>

$ErrorActionPreference = "Stop"
$ArchiveDir = ".archive/docs"

Write-Host "📚 STARTING DOCUMENTATION SANITIZATION..." -ForegroundColor Cyan

# 1. Create Doc Archive
if (-not (Test-Path $ArchiveDir)) {
    New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
}

# 2. Define Zombie Docs (Features Removed in ALPHA-83)
$DocsToArchive = @(
    "docs/observability-dashboard.md",
    "docs/observability-implementation-summary.md",
    "docs/reference/observability.md",
    "docs/ECOSYSTEM_STATUS_REPORT.md",
    "OBSERVABILITY_STATUS.md",
    "MEMOS_PROGRESS_UPDATE.md",
    "OPERATION_ASGARD_REBIRTH_BASELINE.md"
)

foreach ($file in $DocsToArchive) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination $ArchiveDir -Force
        Write-Host "📦 Archived: $file" -ForegroundColor Yellow
    }
}

# 3. Create/Update BUILD.md (The New Truth)
$BuildDocPath = "BUILD.md"
$BuildContent = @"
# Build & Run Guide (v0.1.0-aligned)

## Prerequisites
- Python 3.12+
- Poetry 2.0+
- Docker (Optional)

## Quick Start (Standalone)

```powershell
# Install Dependencies
poetry install

# Run Server (Port 8768)
./scripts/run-standalone.ps1
```

## Docker Build

```powershell
docker build -t memos-mcp:latest .
docker run -p 8768:8768 memos-mcp:latest
```

## Testing

```powershell
# Run Unit Tests
poetry run pytest

# Run Integration (Requires Neo4j)
poetry run pytest -m integration
```
"@

Set-Content -Path $BuildDocPath -Value $BuildContent -Encoding UTF8
Write-Host "✅ Created/Updated: $BuildDocPath" -ForegroundColor Green

Write-Host "✨ DOCUMENTATION CLEANUP COMPLETE." -ForegroundColor Cyan
