# SOMA ORGANISM KNOWLEDGE BASE

**Generated:** 2026-01-30
**Commit:** 53cf8b3
**Branch:** beta

## OVERVIEW

Biomorphic distributed knowledge ecosystem: Senses (InGress FastAPI) → Stomach (InGest metabolism) → Brain (OmegaKG Neo4j) → Hands (memOS MCP). React dashboard (Cortex). Organism executes via `start_ecosystem.ps1`.

## STRUCTURE

```
Soma/
├── InGress/           # Sensory layer (FastAPI port 8000)
├── InGest/            # SimpleMem Stage 1 metabolism
├── OmegaKG/           # Neo4j persistence + capture server (port 8765)
├── memOS/             # FastMCP 2.0 server (port 8768)
├── Cortex/            # React 19 + Vite dashboard (port 5173)
├── OmegaVault/        # Obsidian knowledge vault
├── contracts/         # API contract validation (JSON schemas)
├── scripts/           # Operations (database/, operations/, infrastructure/)
└── orchestrator.py    # Legacy startup (use start_ecosystem.ps1 instead)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Start all services | `start_ecosystem.ps1` | Robust: migrations, health checks, contracts |
| Legacy startup | `orchestrator.py` | Basic spawning, no validation |
| End-to-end verification | `scripts/operations/trace-meal.ps1` | ALWAYS run after changes |
| API contracts | `contracts/*.json` + `validate_contracts.py` | Pre-flight validation |
| Database migrations | `scripts/database/migrate_all.py` | Alembic for all services |
| Signal capture | `InGress/soma_ingress/` | Thin sensory layer |
| Metabolism logic | `InGest/src/ingest_llm_as/` | Heavy digestion (entropy, coreference, temporal) |
| Graph persistence | `OmegaKG/omega_kg/consumer.py` | Redis stream → Neo4j |
| MCP tools | `memOS/src/memos_mcp/logic.py` | Retrieval, scratchpad, promotion |
| Dashboard UI | `Cortex/src/` | Neural telemetry, meal traces |
| Vault integration | `OmegaVault/ApexSigma/Development/Projects/Soma/` | Architecture docs, governance |

## CONVENTIONS

**Hybrid Architecture (Windows + Docker):**
- DATA LAYER: Docker (Postgres:6000, Neo4j:7687, Redis:6380)
- LOGIC LAYER: Host (Python services)
- Host → Docker: Use `localhost:<port>`, NOT container names

**Python (InGress, InGest, OmegaKG, memOS):**
- Poetry-managed, Python 3.12+
- `from __future__ import annotations` required
- Ruff format (line-length 88)
- Type hints MANDATORY for public functions
- Async Neo4j: `async with graph_driver.session()` ALWAYS
- File I/O: `encoding="utf-8"` MANDATORY
- Imports: isort ordering (standard, third-party, local)
- Naming: `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- Error handling: Specific exceptions + structlog context
- NO comments unless explicitly requested

**TypeScript/React (Cortex):**
- Strict TypeScript, no `any` unless critical
- Zustand for global state (no Redux/Context)
- Tailwind CSS classes only (no inline styles)
- ESLint + Prettier enforced
- Components `PascalCase`, functions `camelCase`

**Settings Pattern (Divergent by Service):**
- InGest: `get_settings()` NOT cached (reloads .env each call)
- memOS: Pydantic BaseSettings with `.env` file
- OmegaKG: Bitwarden → env → defaults (`.env.example` canonical)

**Database Patterns:**
- Neo4j: async context managers prevent leaks
- PostgreSQL: SQLAlchemy with context manager sessions
- Redis: Working memory TTL-based cache
- Qdrant: Optional vector search (graceful degradation)

## ANTI-PATTERNS (THIS PROJECT)

❌ **InGress complexity** - Keep sensory layer thin, metabolism goes in InGest
❌ **Container names from host** - Use `localhost:<port>` not `apexsigma.neo4j.soma`
❌ **Skipping meal trace** - ALWAYS verify with `trace-meal.ps1` after changes
❌ **Direct DB instantiation** - Use factories: `get_database()`, `get_settings()`
❌ **Cached settings (InGest)** - Call `get_settings()` fresh each time
❌ **Missing encoding** - File I/O without `encoding="utf-8"` breaks Windows
❌ **Sync Neo4j sessions** - Use async context managers ONLY
❌ **Bypassing contracts** - Validate with `validate_contracts.py` before deploy
❌ **Skipping migrations** - Run `migrate_all.py upgrade` before schema changes hit prod

## UNIQUE STYLES

**Biomorphic Terminology:**
- "Senses" not "API ingestion"
- "Stomach" not "processing pipeline"
- "Brain" not "knowledge graph"
- "Meal Trace" not "end-to-end test"
- "Nervous System" = Redis streams
- "Codex" = Neo4j long-term memory

**Tier Mapping (memOS):**
- MCP_GEMINI/COPILOT/QWEN → Procedural (Tier 2)
- MCP_SYSTEM → Semantic (Tier 3)
- Working memory → Redis (Tier 1)

**Dual Persistence (OmegaKG):**
- Tasks in Neo4j + Obsidian markdown (frontmatter sync)
- Conversations captured to `OmegaVault/AI_Conversations/{platform}/`
- UID-based task naming: `Tasks/**/{uid}*.md`

**Entropy Gate (InGest):**
- H > 0.35 threshold
- Coreference resolution (spaCy/coreferee)
- Temporal anchoring (dateparser)
- Output: AtomicFact digests

**POML Serialization (InGest):**
- XML-based knowledge structures
- See `InGest/prompts/` for examples

## COMMANDS

### Executive Startup (Recommended)
```powershell
# Robust startup with migrations, health checks, contracts
.\start_ecosystem.ps1

# Debug mode (visible windows)
.\start_ecosystem.ps1 -ShowConsole

# Persistent watchdog monitoring
.\start_ecosystem.ps1 -Persistent

# Skip components
.\start_ecosystem.ps1 -SkipMigrations -SkipContracts
```

### Legacy Startup
```powershell
python orchestrator.py  # Basic service spawning
```

### Verification
```powershell
# End-to-end meal trace
.\scripts\operations\trace-meal.ps1

# Cortex live UI test
cd Cortex && npm run dev
# Navigate to http://localhost:5173/#cortex
```

### Testing
```bash
# Python - per organ
poetry run pytest InGress/ InGest/ OmegaKG/ memOS/

# Python - single test
poetry run pytest InGest/tests/test_api.py::test_function -v

# Python - markers
poetry run pytest -m "unit" -m "integration" -m "requires_neo4j"

# Cortex
cd Cortex && npm test
```

### Contracts
```powershell
# Validate all
python contracts/validate_contracts.py

# Validate specific
python contracts/validate_contracts.py ingress ingest omegakg memos
```

### Migrations
```powershell
# Upgrade all
python scripts/database/migrate_all.py upgrade

# Check status
python scripts/database/migrate_all.py status

# Per-service
python scripts/database/migrate_all.py upgrade --service InGest
```

### Quality Gates
```bash
# Python (per organ)
poetry run ruff check --fix . && poetry run ruff format .
poetry run mypy <organ_name>
pre-commit run --all-files

# Cortex
cd Cortex && npm run lint && npm run build
```

## NOTES

**Memory Tiers:**
- Tier 1 (Working): Redis, TTL-based, ephemeral
- Tier 2 (Procedural): PostgreSQL, tools/procedures
- Tier 3 (Semantic): Neo4j + vector, long-term graph

**Service Ports:**
- InGress: 8000
- OmegaKG: 8765 (capture server)
- memOS: 8768 (MCP)
- Cortex: 5173 (dev server)
- Postgres: 6000 (host-mapped)
- Neo4j: 7687 (bolt, host-mapped)
- Redis: 6380 (host-mapped)

**Neo4j Connection Gotcha:**
- OmegaKG auto-switches to mock mode on Neo4j failure
- Health check: `RETURN 1` query
- Always use async context managers

**Vector Embeddings:**
- Qwen3-Embedding (768-dim)
- Placeholder embeddings NOT production-ready
- Qdrant optional, graceful degradation

**Settings Reload (InGest):**
- `get_settings()` reloads .env each call
- Intentional design for dynamic config
- Do NOT cache module-level

**Task Lifecycle (OmegaKG):**
- Draft → Ready → Active → Blocked → Completed → Archived
- Auto-transitions every 5min (APScheduler)
- Dual-write to Neo4j + Obsidian markdown

**Chrome Extension (OmegaKG):**
- JWT exchange: static API key → short-lived tokens
- CORS requires exact extension ID
- Writes to `AI_Conversations/{platform}/`

**Contract Validation:**
- JSON schemas in `contracts/`
- Pre-flight via `validate_contracts.py`
- start_ecosystem.ps1 enforces by default

**Migration Discipline:**
- Alembic per service
- Run `migrate_all.py validate` first
- Match `ENV_TYPE` (dev=ephemeral, stable=locked)

---

*Updated 2026-01-30 - Genesis v2.0 → Beta refinement*
