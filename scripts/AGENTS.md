# SCRIPTS KNOWLEDGE

**Location:** scripts/
**Purpose:** Operations, maintenance, and infrastructure automation

## STRUCTURE

```
scripts/
├── database/          # Migration and schema management
├── operations/        # Daily ops (meal trace, monitoring, restarts)
├── infrastructure/    # Service management, health checks, network
├── maintenance/       # Diagnostics, repairs, config updates
├── testing/           # Smoke tests, integration validation
├── utilities/         # General-purpose tools
└── SCRIPTS_REFERENCE.md  # Canonical script inventory
```

## WHERE TO LOOK

| Task | Script | Notes |
|------|--------|-------|
| Run migrations | `database/migrate_all.py` | Alembic upgrade for all services |
| Meal trace verification | `operations/trace-meal.ps1` | E2E signal flow test |
| Start ecosystem | (use root `start_ecosystem.ps1`) | NOT in scripts/ |
| Service health check | `infrastructure/health-check.py` | All services |
| Restart capture server | `operations/restart-capture-server.ps1` | OmegaKG only |
| MCP config repair | `maintenance/repair-mcp-robust.py` | Fix memOS config |
| Monitor dashboard | `operations/monitor-dashboard.ps1` | Live service status |
| Neo4j vector indexes | `infrastructure/soma-vector-indexes.cypher` | Graph setup |

## CONVENTIONS

**PowerShell Scripts (.ps1):**
- Execution policy: `RemoteSigned` or higher
- Load env via `load_env.ps1` if needed
- Use `Write-Host` for output
- Error handling: `try/catch` + `$ErrorActionPreference`

**Python Scripts (.py):**
- Shebang: `#!/usr/bin/env python3`
- Use project env: `poetry run python <script>`
- Settings from .env via `python-dotenv`
- Logging: `logging.getLogger(__name__)`

**Cypher Scripts (.cypher):**
- Neo4j console or `cypher-shell`
- Idempotent: use `CREATE INDEX IF NOT EXISTS`
- Comments: `// Description`

**Naming:**
- Action-noun format: `restart-service.ps1`, `verify-migration.py`
- Hyphens in PowerShell, underscores in Python

## ANTI-PATTERNS

❌ **Hardcoded paths** - Use env vars or relative paths
❌ **No error handling** - Always catch/log failures
❌ **Silent failures** - Output status messages
❌ **Direct service edits** - Use service management scripts

## COMMANDS

### Database
```bash
# Run all migrations
poetry run python scripts/database/migrate_all.py upgrade

# Check migration status
poetry run python scripts/database/migrate_all.py status
```

### Operations
```powershell
# Meal trace verification
.\scripts\operations\trace-meal.ps1

# Monitor dashboard
.\scripts\operations\monitor-dashboard.ps1

# Restart capture server
.\scripts\operations\restart-capture-server.ps1
```

### Infrastructure
```bash
# Health check all services
poetry run python scripts/infrastructure/health-check.py

# Service manager
poetry run python scripts/infrastructure/service-manager.py status
```

### Maintenance
```powershell
# Repair MCP config
poetry run python scripts/maintenance/repair-mcp-robust.py

# Diagnose spaCy models
.\scripts\maintenance\diagnose-spacy-models.ps1
```

## NOTES

**Migration Discipline:**
- `migrate_all.py` coordinates Alembic across services
- Always run `status` before `upgrade`
- Match `ENV_TYPE` (dev/stable) to target environment

**Meal Trace:**
- `trace-meal.ps1` sends test signal through full pipeline
- Verifies: InGress → Postgres → InGest → Redis → OmegaKG → Neo4j
- MUST pass before production deploys

**Service Management:**
- Prefer `start_ecosystem.ps1` (root) over individual scripts
- Individual restart scripts for debugging specific services
- `service-manager.py` for advanced orchestration

**Health Checks:**
- `health-check.py` queries all service `/health` endpoints
- Returns aggregated status (online/degraded/offline)
- Used by `start_ecosystem.ps1` for readiness gates

**MCP Repairs:**
- `repair-mcp-robust.py` fixes Claude Desktop config
- Validates JSON, MCP connection, tool registry
- Auto-backup before modifications

**Archive:**
- `archive/` contains deprecated/historical scripts
- DO NOT use archived scripts without review
- Check git history for context

---

*Parent: [../AGENTS.md](../AGENTS.md)*
*Reference: [SCRIPTS_REFERENCE.md](SCRIPTS_REFERENCE.md)*
