# AGENTS.md

**Purpose:** Entry point for agents working with the Soma ecosystem. This document provides modular guidance for coding, testing, architecture, and the biomorphic signal pipeline (Senses -> Stomach -> Brain).

**Last Updated:** 2026-01-28 (Soma Genesis v2.0)

---

## Quick Start

- **Read this file** for the biomorphic mental model.
- **Executive Workflow (Robust):** Use `start_ecosystem.ps1` to manage all services with health checks, migrations, and contract validation.
- **Executive Workflow (Debug):** Use `orchestrator.py` for basic service spawning.
- **Verification:** Always run `.\scripts\operations\trace-meal.ps1` after changes.
- **Contract Validation:** Use `python contracts/validate_contracts.py` to verify service contracts.
- **Migrations:** Use `python scripts/database/migrate_all.py upgrade` for database schema updates.
- **Vault Root:** `OmegaVault/ApexSigma/Development/Projects/Soma/`

---

## Essential Commands

### Executive Life-Support (Recommended)

```powershell
# Robust startup with health checks, migrations, and contract validation
.\start_ecosystem.ps1

# Debug mode (visible windows)
.\start_ecosystem.ps1 -ShowConsole

# Persistent mode (watchdog monitoring)
.\start_ecosystem.ps1 -Persistent

# Combined flags
.\start_ecosystem.ps1 -ShowConsole -Persistent

# Skip specific components
.\start_ecosystem.ps1 -SkipMigrations -SkipContracts
```

### Legacy Executive Life-Support

```powershell
python orchestrator.py  # Start all organs (Senses, Stomach, Brain, Hands)
```

### Testing & Verification

```powershell
# End-to-End Meal Trace
.\scripts\operations\trace-meal.ps1

# Cortex Bridge Neural Telemetry (Live UI Test)
cd Cortex && npm run dev
# Navigate to http://localhost:5173/#cortex

# Python - Run all tests in an organ
poetry run pytest InGress/ InGest/ OmegaKG/ memOS/

# Python - Run single test file or function
poetry run pytest InGest/tests/test_api.py -v
poetry run pytest InGest/tests/test_api.py::test_specific_function -v

# Python - Run tests by marker
poetry run pytest -m "unit" -m "integration" -m "not slow" -m "requires_neo4j"

# Cortex (TypeScript/React) tests
cd Cortex && npm test
cd Cortex && npm test -- src/components/Button.test.tsx
```

### API Contracts & Validation

```powershell
# Validate all service contracts
python contracts/validate_contracts.py

# Validate specific services
python contracts/validate_contracts.py ingress ingest omegakg memos

# Check contract status
Get-Content contracts\*_contract.json | ConvertFrom-Json
```

**Contract Files:**
- `contracts/ingress_contract.json` - InGress API specification
- `contracts/ingest_contract.json` - InGest API specification
- `contracts/omegakg_contract.json` - OmegaKG API specification
- `contracts/memos_contract.json` - memOS API specification

**See:** [contracts/README.md](contracts/README.md) for detailed contract documentation

### Database Migrations

```powershell
# Upgrade all services to latest migrations
python scripts/database/migrate_all.py upgrade

# Check migration status
python scripts/database/migrate_all.py status

# Validate migration configuration
python scripts/database/migrate_all.py validate

# Upgrade specific service
python scripts/database/migrate_all.py upgrade --service InGest

# Downgrade migrations (one revision)
python scripts/database/migrate_all.py downgrade --service InGest
```

**Migration Management:**
- All services use Alembic for database migrations
- Migrations are stored in `alembic/versions/` directories
- Run `migrate_all.py validate` to check configuration

### Quality Gates

```bash
# Python (run from each organ directory)
pre-commit run --all-files
poetry run ruff check --fix . && poetry run ruff format .
poetry run mypy <organ_name>

# Cortex (TypeScript/React)
npm run lint && npm run build
```

---

## Code Style Guidelines

### Python (InGest, InGress, OmegaKG, memOS)

**Imports:** `isort` ordering (standard, third-party, local). No `from module import *`. Use `from __future__ import annotations` for Python 3.12+.

**Formatting:** Ruff with line-length 88. Run `poetry run ruff format .` before committing.

**Types:** Use type hints. Return type annotations required for public functions.

**Naming:** Functions `snake_case`, Classes `PascalCase`, Constants `UPPER_SNAKE_CASE`, Private methods `_leading_underscore`.

**Error Handling:** Use specific exceptions. FastAPI endpoints raise `HTTPException`. Always log errors with context.

```python
from fastapi import HTTPException
from structlog import get_logger

logger = get_logger(__name__)

try:
    result = await process_data(data)
except ValueError as e:
    logger.error("Invalid data", error=str(e), data=data)
    raise HTTPException(status_code=400, detail=f"Invalid data: {e}")
```

**File I/O:** ALWAYS specify `encoding="utf-8"`.

```python
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
```

**Async Patterns:** Use async context managers for Neo4j/Redis sessions.

```python
async with graph_driver.session() as session:
    result = await session.run("MATCH (n) RETURN n LIMIT 1")
    record = await result.single()
```

**Comments:** NO comments unless explicitly requested.

### TypeScript/React (Cortex)

**Imports:** ES6 imports. No default imports for named exports.

**Formatting:** ESLint + Prettier. Run `npm run lint` to check.

**Types:** Strict TypeScript mode. No `any` unless absolutely necessary. Use interfaces for object shapes.

**Naming:** Components `PascalCase`, Functions `camelCase`, Constants `UPPER_SNAKE_CASE`, Types/Interfaces `PascalCase`.

**Error Handling:** Try/catch with toasts for user feedback.

**Styling:** Tailwind CSS classes. Avoid inline styles. Custom tokens in `index.css`.

**State Management:** Zustand stores. No Redux/Context API for global state.

---

## Top 5 Critical Patterns (The Soma Mental Model)

### 1. The Meal Trace (E2E)

**Architecture:** Senses (InGress) → Lake (Postgres) → Stomach (InGest) → Nervous System (Redis) → Brain (OmegaKG) → Persistence (Neo4j).

**Pattern:** Never assume a service is "working" just because it's running. Always verify the *flow* of a signal through the entire organism.

### 2. SimpleMem Stage 1 (Metabolism)

**Process:** Signal arrives in Stomach → Entropy Gate (H > 0.35) → Coreference Resolution → Temporal Anchoring → Atomic Fact Synthesis.

**Constraint:** InGest is the heavy-lifter. InGress must remain a thin sensory layer.

### 3. Neo4j Async Context Managers MANDATORY

**CRITICAL:** Always use async context managers for Neo4j sessions to prevent connection leaks.

### 4. UTF-8 Encoding Required

**CRITICAL:** All file I/O must specify `encoding="utf-8"`.

### 5. Distributed DNS (Windows Host Access)

**Pattern:** For services on Windows host connecting to Docker containers:
- Use `localhost:<port>` for Postgres (6000), Neo4j (7687), Redis (6380).
- DO NOT use container names (e.g., `apexsigma.neo4j.soma`) from the host logic layer.

---

## Governance Documentation Index

| Organ | Function | Document |
| :--- | :--- | :--- |
| **Senses** | Signal Capture | `InGress/README.md` |
| **Stomach** | Metabolism | `InGest/README.md` |
| **Brain** | Persistence | `OmegaKG/README.md` |
| **Hands** | Actions (MCP) | `memOS/README.md` |
| **Dashboard** | UI/Visualization | `Cortex/README.md` |

---

## Component Coverage

- **InGress**: FastAPI sensory layer (Port 8000).
- **InGest**: SimpleMem Stage 1 metabolism poller.
- **OmegaKG**: Neo4j persistence consumer (Port 8765/Consumer Group).
- **memOS**: FastMCP 2.0 server (Port 8768).
- **Cortex**: React 19 + TypeScript dashboard (Vite, Port 5173).

---

*Keep this documentation alive. Update as the organism evolves.*
