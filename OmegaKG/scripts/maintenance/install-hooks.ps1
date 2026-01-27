#!/usr/bin/env pwsh
# Omega_KG Git Hook Auto-Installer
# Finds all Git repos and installs post-commit hooks

param(
    [string[]]$Paths = @(
        "$env:USERPROFILE\Documents\GitHub",
        "$env:USERPROFILE\projects",
        "C:\projects"
    ),
    [switch]$DryRun,
    [switch]$Force,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

# Locate hook template
$scriptDir = Split-Path -Parent $PSCommandPath
$hookTemplate = Join-Path $scriptDir "..\hooks\post-commit"
$hookTemplatePs1 = Join-Path $scriptDir "..\hooks\post-commit.ps1"

if (-not (Test-Path $hookTemplate) -and -not (Test-Path $hookTemplatePs1)) {
    Write-Error "Hook template not found. Run this from Omega_KG repo."
}

# Registry of installed hooks (for tracking/uninstall)
$registryPath = Join-Path $scriptDir "..\hooks\installed-repos.txt"

function Find-GitRepos {
    param([string[]]$SearchPaths)

    $repos = @()
    foreach ($path in $SearchPaths) {
        if (Test-Path $path) {
            $repos += Get-ChildItem -Path $path -Directory -Recurse -Filter ".git" -ErrorAction SilentlyContinue |
                ForEach-Object { $_.Parent.FullName }
        }
    }
    return $repos | Sort-Object -Unique
}

# Returns the installed hook version from the given hook file path.
# If the hook file does not exist, returns "0.0.0".
# If the version cannot be determined, returns "unknown".
function Get-InstalledHookVersion {
    param([string]$HookPath)

    if (-not (Test-Path $HookPath)) { return "0.0.0" }

    $content = Get-Content $HookPath -Raw
    if ($content -match 'HOOK_VERSION="([0-9.]+)"') {
        return $matches[1]
    }
    return "unknown"
}

function Install-Hook {
    param(
        [string]$RepoPath,
        [string]$HookSource,
        [bool]$IsUninstall = $false
    )

    $hookDest = Join-Path $RepoPath ".git\hooks\post-commit"
    $repoName = Split-Path -Leaf $RepoPath

    # In Install-Hook function:
    $currentVersion = Get-InstalledHookVersion -HookPath $hookDest
    $newVersion = "1.0.0"  # Read from template

    if ($currentVersion -eq $newVersion -and -not $Force) {
        Write-Host "  ⊗ Up to date: $repoName (v$currentVersion)" -ForegroundColor Gray
        return $false
    }

    if ($IsUninstall) {
        if (Test-Path $hookDest) {
            # Verify it's our hook before deleting
            $content = Get-Content $hookDest -Raw
            if ($content -match "Omega_KG") {
                # Optional: If you need to extract a group, check $matches
                # (No group extraction needed; redundant inner match removed)
                Remove-Item $hookDest -Force
                Write-Host "  ✓ Uninstalled from: $repoName" -ForegroundColor Yellow
                return $true
            } else {
                Write-Host "  ⊗ Skipped (not Omega_KG hook): $repoName" -ForegroundColor Gray
                return $false
            }
        }
        return $false
    }

    # Check if hook exists
    if ((Test-Path $hookDest) -and -not $Force) {
        $content = Get-Content $hookDest -Raw
        if ($content -match "Omega_KG") {
            Write-Host "  ⊗ Already installed: $repoName" -ForegroundColor Gray
            return $false
        }
    }

    # Install the hook
    Copy-Item -Path $HookSource -Destination $hookDest -Force
    Write-Host "  ✓ Installed: $repoName" -ForegroundColor Green
    return $true
}

# Main execution
Write-Host "🔍 Scanning for Git repositories..." -ForegroundColor Cyan

$repos = Find-GitRepos -SearchPaths $Paths
Write-Host "   Found $($repos.Count) repositories`n" -ForegroundColor Gray

if ($DryRun) {
    Write-Host "🏃 DRY RUN MODE (no changes will be made)`n" -ForegroundColor Yellow
}

$installed = 0
$skipped = 0
$failed = 0

foreach ($repo in $repos) {
    $repoName = Split-Path -Leaf $repo

    if ($DryRun) {
        Write-Host "  [DRY] Would install to: $repoName" -ForegroundColor Gray
        continue
    }

    try {
        # Prefer bash hook, fallback to PowerShell
        $hookSource = if (Test-Path $hookTemplate) { $hookTemplate } else { $hookTemplatePs1 }

        $result = Install-Hook -RepoPath $repo -HookSource $hookSource -IsUninstall:$Uninstall

        if ($result) {
            $installed++
            # Track installation
            if (-not $Uninstall) {
                Add-Content -Path $registryPath -Value $repo
            }
        } else {
            $skipped++
        }
    } catch {
        Write-Host "  ✗ Failed: $repoName - $_" -ForegroundColor Red
        $failed++
    }
}

# Summary
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
if ($Uninstall) {
    Write-Host "Uninstalled: $installed | Skipped: $skipped | Failed: $failed" -ForegroundColor Yellow
} else {
    Write-Host "Installed: $installed | Skipped: $skipped | Failed: $failed" -ForegroundColor Green
}

if ($installed -gt 0 -and -not $Uninstall) {
    Write-Host "`n✨ Hook installation complete!" -ForegroundColor Cyan
    Write-Host "   Next commit in any repo will log to Obsidian session notes." -ForegroundColor Gray
}
