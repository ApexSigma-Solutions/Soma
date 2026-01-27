<#
.SYNOPSIS
    Manually percolate AI conversation files into Neo4j knowledge graph.

.DESCRIPTION
    This script scans the AI_Conversations folder in your Obsidian vault and
    percolates conversations into Neo4j. Supports date range filtering to
    re-process specific time periods.

.PARAMETER StartDate
    Start date for percolation (inclusive). Format: YYYY-MM-DD
    Default: 30 days ago

.PARAMETER EndDate
    End date for percolation (inclusive). Format: YYYY-MM-DD
    Default: today

.PARAMETER Platform
    Filter by AI platform (Gemini, Claude, ChatGPT, etc.). Leave empty for all.

.PARAMETER DryRun
    Show what would be percolated without actually doing it.

.EXAMPLE
    .\percolate-conversations.ps1
    Percolate all conversations from the last 30 days

.EXAMPLE
    .\percolate-conversations.ps1 -StartDate "2025-11-19" -EndDate "2025-11-20"
    Percolate conversations from Nov 19-20, 2025

.EXAMPLE
    .\percolate-conversations.ps1 -Platform "Gemini" -StartDate "2025-11-01"
    Percolate only Gemini conversations since November 1st

.EXAMPLE
    .\percolate-conversations.ps1 -DryRun
    Preview what would be percolated without making changes
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$StartDate = (Get-Date).AddDays(-30).ToString("yyyy-MM-dd"),

    [Parameter(Mandatory=$false)]
    [string]$EndDate = (Get-Date).ToString("yyyy-MM-dd"),

    [Parameter(Mandatory=$false)]
    [string]$Platform = "",

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Load environment variables
$envPath = Join-Path $PSScriptRoot ".." ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$vaultPath = $env:OBSIDIAN_VAULT_PATH
if (-not $vaultPath -or -not (Test-Path $vaultPath)) {
    Write-Host "❌ Error: OBSIDIAN_VAULT_PATH not set or invalid" -ForegroundColor Red
    exit 1
}

$conversationsPath = Join-Path $vaultPath "AI_Conversations"
if (-not (Test-Path $conversationsPath)) {
    Write-Host "❌ Error: AI_Conversations folder not found at: $conversationsPath" -ForegroundColor Red
    exit 1
}

# Parse dates
try {
    $startDateTime = [DateTime]::ParseExact($StartDate, "yyyy-MM-dd", $null)
    $endDateTime = [DateTime]::ParseExact($EndDate, "yyyy-MM-dd", $null).AddDays(1).AddSeconds(-1)
} catch {
    Write-Host "❌ Error: Invalid date format. Use YYYY-MM-DD" -ForegroundColor Red
    exit 1
}

Write-Host "🔍 Scanning for AI conversations..." -ForegroundColor Cyan
Write-Host "   Vault: $vaultPath" -ForegroundColor Gray
Write-Host "   Date range: $StartDate to $EndDate" -ForegroundColor Gray
if ($Platform) {
    Write-Host "   Platform filter: $Platform" -ForegroundColor Gray
}
if ($DryRun) {
    Write-Host "   🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}
Write-Host ""

# Find all conversation files
$allFiles = Get-ChildItem -Path $conversationsPath -Filter "*.md" -Recurse

# Filter by platform if specified
if ($Platform) {
    $platformPath = Join-Path $conversationsPath $Platform
    if (Test-Path $platformPath) {
        $allFiles = Get-ChildItem -Path $platformPath -Filter "*.md" -Recurse
    } else {
        Write-Host "⚠️  Warning: Platform folder '$Platform' not found" -ForegroundColor Yellow
        $allFiles = @()
    }
}

# Filter by date range (based on file last write time)
$filteredFiles = $allFiles | Where-Object {
    $_.LastWriteTime -ge $startDateTime -and $_.LastWriteTime -le $endDateTime
} | Sort-Object LastWriteTime

if ($filteredFiles.Count -eq 0) {
    Write-Host "ℹ️  No conversation files found matching criteria" -ForegroundColor Yellow
    exit 0
}

Write-Host "📊 Found $($filteredFiles.Count) conversation file(s) to process" -ForegroundColor Green
Write-Host ""

if ($DryRun) {
    Write-Host "Files that would be percolated:" -ForegroundColor Cyan
    $filteredFiles | ForEach-Object {
        $relativePath = $_.FullName.Substring($conversationsPath.Length + 1)
        Write-Host "  • $relativePath [$($_.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))]" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "✅ Dry run complete. Use without -DryRun to percolate these files." -ForegroundColor Green
    exit 0
}

# Activate virtual environment and run percolation
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot

try {
    Write-Host "🚀 Starting percolation..." -ForegroundColor Cyan
    Write-Host ""

    $processedCount = 0
    $errorCount = 0

    foreach ($file in $filteredFiles) {
        $relativePath = $file.FullName.Substring($conversationsPath.Length + 1)
        Write-Host "📝 Processing: $relativePath" -ForegroundColor White

        try {
            # Read the markdown file
            $content = Get-Content $file.FullName -Raw

            # Extract platform from path
            $platform = Split-Path (Split-Path $file.FullName -Parent) -Leaf

            # Call Python percolation directly
            $pythonCmd = @"
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, r'$projectRoot')

from omega_kg.percolation import percolate_conversation
from omega_kg.settings import settings

# Read the conversation file
file_path = r'$($file.FullName)'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Percolate
try:
    result = percolate_conversation(content, platform='$platform', source_file=file_path)
    print(f'OK: Created {result.get("nodes_created", 0)} nodes, {result.get("relationships_created", 0)} relationships')
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {str(e)}')
    sys.exit(1)
"@

            $tempPyFile = Join-Path $env:TEMP "percolate_temp_$(Get-Random).py"
            $pythonCmd | Out-File -FilePath $tempPyFile -Encoding UTF8

            $result = & poetry run python $tempPyFile 2>&1
            Remove-Item $tempPyFile -ErrorAction SilentlyContinue

            if ($LASTEXITCODE -eq 0) {
                Write-Host "   $result" -ForegroundColor Green
                $processedCount++
            } else {
                Write-Host "   $result" -ForegroundColor Red
                $errorCount++
            }

        } catch {
            Write-Host "   ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
            $errorCount++
        }

        Write-Host ""
    }

    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "✅ Percolation complete!" -ForegroundColor Green
    Write-Host "   Processed: $processedCount files" -ForegroundColor Green
    if ($errorCount -gt 0) {
        Write-Host "   Errors: $errorCount files" -ForegroundColor Yellow
    }
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan

} finally {
    Pop-Location
}
