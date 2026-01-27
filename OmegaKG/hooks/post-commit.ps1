#!/usr/bin/env pwsh
# Post-commit hook for Omega_KG
# This hook runs after each commit to ensure quality gates

param()

$ErrorActionPreference = "Stop"

# Check if we're in the Omega_KG repo
if (-not (Test-Path ".pre-commit-config.yaml")) {
    Write-Host "Not in Omega_KG repo, skipping post-commit checks."
    exit 0
}

# Run pre-commit on the last commit
try {
    & poetry run pre-commit run --from-ref HEAD~1 --to-ref HEAD --all-files
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Pre-commit checks failed. Please fix issues and amend the commit."
    }
} catch {
    Write-Warning "Failed to run pre-commit: $_"
}
