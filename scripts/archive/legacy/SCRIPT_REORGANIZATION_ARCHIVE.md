---
DEPRECATED: Legacy scripts moved to archive.
Current scripts use kebab-case naming and functional categorization.
Last reviewed: 2025-01-08
---

# Legacy Scripts Archive

*All scripts have been moved to appropriate categories in `scripts/` with standardized naming.*

## Script Category Migration

### Database Operations
- `verify-phase2-readiness.py` → `scripts/database/verify-phase2-readiness.py`

### Maintenance Operations  
- `fix_profile.ps1` → `scripts/maintenance/fix-powershell-profile.ps1`
- `force_fix_v2.ps1` → `scripts/maintenance/force-profile-fix-v2.ps1`
- `force_profile_update.ps1` → `scripts/maintenance/force-profile-update.ps1`
- `repair_mcp_config.py` → `scripts/maintenance/repair-mcp-configuration.py`
- `robust_repair_mcp.py` → `scripts/maintenance/repair-mcp-robust.py`
- `update_agent_config.py` → `scripts/maintenance/update-agent-configuration.py`
- `update_prompt.ps1` → `scripts/maintenance/update-prompt.ps1`

### Operations
- `run_phase2_audit.ps1` → `scripts/testing/run-phase2-audit.ps1`
- `run-multi-project.ps1` → `scripts/operations/start-multi-project.ps1`
- `run-multi-project.sh` → `scripts/operations/start-multi-project.sh`

### Utilities
- `init.ps1` → `scripts/utilities/initialize-shell-integration.ps1`
- `process-events.py` → `scripts/utilities/process-events.py`

---

## Current Script Structure

```
scripts/
├── database/           # Database operations and verification
├── maintenance/        # System maintenance and repairs
├── operations/         # Service startup and multi-project
├── testing/           # Diagnostics and audits
├── utilities/         # General utility scripts
└── archive/           # Legacy and deprecated scripts
```

---

**Action**: Use standardized scripts from categorized directories.