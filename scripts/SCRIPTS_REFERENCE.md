# Scripts Reference

This document provides a comprehensive reference for all scripts in the OmegaKG project, organized by functional category.

## Directory Structure

```
scripts/
├── database/              # Database operations and verification
├── maintenance/           # System maintenance and diagnostics
├── operations/            # Service startup and monitoring
├── testing/               # Diagnostic, auth verification, and audit scripts
├── utilities/             # General utility scripts
└── archive/               # Legacy (do not use)
```

## Operations Scripts (Start Here)

### launch-unified.ps1
**Purpose**: Primary entry point to start the entire OmegaKG ecosystem
**Usage**: `./scripts/operations/launch-unified.ps1`
**Description**: Launches Capture Server, InGest-LLM, and memOS components

### restart-capture-server.ps1
**Purpose**: Restart only the Capture Server service
**Usage**: `./scripts/operations/restart-capture-server.ps1`
**Description**: Fast restart for backend logic changes

### monitor-dashboard.ps1
**Purpose**: Monitor ecosystem health dashboard
**Usage**: `./scripts/operations/monitor-dashboard.ps1`
**Description**: Real-time monitoring of service status

### start-multi-project.ps1
**Purpose**: Start multiple projects simultaneously (Low-level)
**Usage**: `./scripts/operations/start-multi-project.ps1`

## Maintenance Scripts

### verify-mcp-config.py
**Purpose**: Verify and debug MCP configuration and connectivity
**Usage**: `poetry run python scripts/maintenance/verify-mcp-config.py`
**Description**: Checks .mcp.json, env vars, and service health

### diagnose-spacy-models.ps1
**Purpose**: Diagnose Spacy model installation issues
**Usage**: `./scripts/maintenance/diagnose-spacy-models.ps1`
**Description**: Verifies model paths and loading in Poetry env

### repair-mcp-configuration.py
**Purpose**: Repair MCP configuration files
**Usage**: `poetry run python scripts/maintenance/repair-mcp-configuration.py`

### fix-powershell-profile.ps1 / force-profile-update.ps1
**Purpose**: Fix PowerShell profile configuration
**Usage**: `./scripts/maintenance/fix-powershell-profile.ps1`

## database Scripts

### verify-phase2-readiness.py
**Purpose**: Verify Phase 2 readiness
**Usage**: `poetry run python scripts/database/verify-phase2-readiness.py`

## Testing Scripts

### verify-neo4j-auth.py
**Purpose**: Verify Neo4j authentication and connectivity
**Usage**: `poetry run python scripts/testing/verify-neo4j-auth.py`

### run-phase2-audit.ps1
**Purpose**: comprehensive system audit
**Usage**: `./scripts/testing/run-phase2-audit.ps1`

## Utilities Scripts

### extract-tn-sections.py
**Purpose**: Extract technical notes from markdown
**Usage**: `poetry run python scripts/utilities/extract-tn-sections.py`

### initialize-shell-integration.ps1
**Purpose**: Initialize shell aliases
**Usage**: `./scripts/utilities/initialize-shell-integration.ps1`

---
**Last Updated**: 2026-01-15
**Status**: Active