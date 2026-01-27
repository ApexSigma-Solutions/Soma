#!/usr/bin/env pwsh
<#
.SYNOPSIS
Claude Code Wrapper for VS Code Extension on Windows
.DESCRIPTION
This PowerShell script properly invokes the npm-installed Claude Code CLI
through cmd.exe to handle .cmd batch file execution.
#>

$ClaudeCmdPath = Join-Path $env:APPDATA "npm\claude.cmd"

# Get all arguments passed to the script
$Args = $args

# Verify the claude.cmd exists
if (-not (Test-Path $ClaudeCmdPath)) {
    Write-Error "Claude Code not found at $ClaudeCmdPath"
    Write-Error "Please ensure @anthropic-ai/claude-code is installed globally via npm"
    exit 1
}

# Execute through cmd.exe to properly handle .cmd files
& cmd.exe /c "`"$ClaudeCmdPath`" $Args"
