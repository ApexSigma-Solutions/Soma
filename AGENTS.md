# AGENTS.md

**Purpose:** Entry point for agents working with OmegaKG codebase. Governance documentation provides detailed, modular guidance for coding, testing, architecture, and data flows.

**Last Updated:** 2025-01-07

---

## Quick Start

**Time to first navigation:** 2 minutes
- **Read this file** for quick reference (essential commands, top 5 patterns)
- **Jump to relevant governance docs** based on your task type (see "Governance Documentation Index" below)
- **Use `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/`** for all detailed patterns and examples

**How to use this system:**
1. Identify your task type (coding, testing, debugging, architecture)
2. Find relevant section in "Governance Documentation Index"
3. Read linked governance document for detailed patterns
4. Follow patterns, execute task
5. Record significant discoveries to memos.MCP (see `07-MIRMIR_PROTOCOL/`)

---

## Essential Commands

### Testing

```bash
# Run single test
poetry run pytest tests/test_filename.py::test_function_name -v

# Run with markers
poetry run pytest -m "unit"
poetry run pytest -m "requires_neo4j"

# Coverage
poetry run pytest --cov=omega_kg --cov-report=html
```

### Code Quality

```bash
# Lint (check for errors)
poetry run ruff check .
poetry run ruff check . --fix  # Auto-fix issues

# Format (apply style)
poetry run ruff format .

# Type checking
poetry run mypy omega_kg/

# Pre-commit hooks (run all checks)
poetry run pre-commit run --all-files
```

### Services

```bash
# Capture server (port 8765)
poetry run capture-server

# CLI commands
poetry run omega lifecycle --dry-run
poetry run omega sync
poetry run omega stats

# Verify config
poetry run python -c "from omega_kg.settings import Settings; print('✓ Settings loaded')"

# Example: Verify system health
poetry run python scripts/database/verify-phase2-readiness.py
```

---

## Top 5 Critical Patterns (Non-Obvious)

**Memorize these immediately - referenced throughout codebase:**

### 1. Neo4j Async Context Managers MANDATORY

**CRITICAL:** Always use async context managers for Neo4j sessions to prevent connection leaks.

```python
# CORRECT ✅
async with graph_driver.session() as session:
    result = await session.run("MATCH (n) RETURN n LIMIT 1")
    record = await result.single()

# INCORRECT ❌
session = graph_driver.session()
result = await session.run("MATCH (n) RETURN n LIMIT 1")
session.close()  # Leak!
```

**Reference:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/05-DATABASES/NEO4J_PATTERNS.md` | Code: `omega_kg/capture_server.py:165`

---

### 2. Vector Queue → InGest-LLM.as → KG Pipeline

**Architecture:** Conversations captured → PostgreSQL (status='pending_embedding') → Background worker → Embeddings → pgvector → Neo4j ChatSession with embedding property

```python
# Capture server queues embedding (non-blocking)
await store_pending(conversation_hash)

# Background worker processes embeddings (polls every 10s)
# See: omega_kg/workers/embedding_worker.py

# Completed embeddings stored in pgvector table
# See: omega_kg/vector_store.py

# Neo4j ChatSession nodes updated with embedding property
```

**Reference:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/06-DATA_FLOWS/CURRENT_PIPELINE.md` | Code: `omega_kg/capture_server.py:155`, `omega_kg/vector_store.py:1`

---

### 3. Single-Instance Development (Hardened System)

**Current State:** No multi-environment switching (Stable/Dev/Temp obsolete). One instance per service across workspace.

```python
# Old: NO - Environment switching logic removed
# New: YES - Single instance with confidence to modify live system
```

**Reference:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/08-SYSTEM_ARCHITECTURE/SINGLE_INSTANCE_DEV.md` | Code: `omega_kg/settings.py:293`

---

### 4. UTF-8 Encoding Required

**CRITICAL:** All file I/O must specify `encoding="utf-8"`.

```python
# CORRECT ✅
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

# INCORRECT ❌
with open(filepath, "w") as f:
    f.write(content)  # Platform-dependent encoding
```

**Reference:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/10-CRITICAL_GOTCHAS/ENCODING_ISSUES.md` | Code: `omega_kg/lifecycle.py:366`

---

### 5. JWT Exchange for Chrome Extension

**Flow:** Extension exchanges static API key for short-lived JWT tokens.

```python
# Extension: POST /auth with static API key
# Server: Returns JWT token (expires in X minutes)
# Extension: Uses JWT for subsequent API calls
```

**Reference:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/09-SECURITY/JWT_FLOW.md` | Code: `omega_kg/capture_server.py:695-716`

---

## Governance Documentation Index

# OmegaKG Ecosystem Context

> [!CAUTION]
> **WINDOWS DOCKER NETWORKING WARNING**
> Due to Windows Docker networking limitations, we use a **Hybrid Architecture**:
> *   **DATA LAYER**: Redis, PostgreSQL (pgvector), and Neo4j run in **Docker Containers**.
> *   **LOGIC LAYER**: OmegaKG, memOS.MCP, and InGest-LLM run **natively on the Host**.
> *   **DO NOT** attempt to containerize the application logic services.
> *   **ALWAYS** ensure containers map ports to `localhost` for host access.

# Project Standards and Guidelines

### By Task Type

**I want to...** | **Read this first** | **Then explore**
|----------------|-----------------|------------------|
| Write code | `AGENTS.md` (this file) | `02-CODING_STANDARDS/CODE_STYLE.md` | Other coding standards |
| Fix a test | `AGENTS.md` → Essential Commands | `03-TESTING/PYTEST_GUIDE.md` | Test markers |
| Add new service | `AGENTS.md` → Essential Commands | `04-SERVICES/` (existing service docs) |
| Understand vector flow | `AGENTS.md` → Top 5 Patterns | `06-DATA_FLOWS/CURRENT_PIPELINE.md` | Data flows |
| Record to memos | `AGENTS.md` → Top 5 Patterns | `07-MIRMIR_PROTOCOL/RECORDING_WORKFLOW.md` | Recording workflow |
| Debug Neo4j issue | `AGENTS.md` → Essential Commands | `05-DATABASES/NEO4J_PATTERNS.md` | Connection leaks |
| Use JWT auth | `AGENTS.md` → Top 5 Patterns | `09-SECURITY/JWT_FLOW.md` | Security docs |

### By Section

| Section | Purpose | Location | Status |
|----------|---------|-----------|--------|
| **Entry Point** | Quick navigation, essential commands | `/AGENTS.md` | ✅ READY |
| **Agent Workflow** | Decision-making, recording to memos | `01-AGENT_WORKFLOW/` | 📋 TO CREATE |
| **Coding Standards** | Style, types, async patterns | `02-CODING_STANDARDS/` | 📋 TO CREATE |
| **Testing** | Pytest, markers, fixtures | `03-TESTING/` | 📋 TO CREATE |
| **Services** | Components, CLI, lifecycle | `04-SERVICES/` | 📋 TO CREATE |
| **Databases** | Neo4j, pgvector, migrations | `05-DATABASES/` | 📋 TO CREATE |
| **Data Flows** | Current pipeline, future vault flow | `06-DATA_FLOWS/` | 📋 TO CREATE |
| **Mirmir Protocol** | memos.MCP integration | `07-MIRMIR_PROTOCOL/` | 📋 TO CREATE |
| **System Architecture** | Single-instance, component map | `08-SYSTEM_ARCHITECTURE/` | 📋 TO CREATE |
| **Security** | JWT, CORS, Bitwarden | `09-SECURITY/` | 📋 TO CREATE |
| **Critical Gotchas** | Common pitfalls, leaks | `10-CRITICAL_GOTCHAS/` | 📋 TO CREATE |

---

## Legacy Code References

**Status: DOCUMENTED AS HISTORICAL**

The following patterns are **legacy** and preserved for understanding historical code, but should NOT be used in new code:

### Obsolete: Multi-Environment Switching

**Legacy Pattern:**
```python
# OLD: Multiple instances with environment switching
omega_env = os.getenv("OMEGA_ENV", "dev").strip().lower()
if omega_env == "stable":
    # stable config
elif omega_env == "dev":
    # dev config
```

**Current Reality:**
- Single instance per service across entire workspace
- No environment-specific ports/paths configuration
- Confidence to modify live system (quick error correction)

**Reference:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/08-SYSTEM_ARCHITECTURE/SINGLE_INSTANCE_DEV.md`

---

### Obsolete: AI_Conversations → Vault Flow

**Legacy Pattern:**
```python
# OLD: Conversations written directly to Obsidian vault
ai_conv_path = vault_path / "AI_Conversations" / platform_folder
```

**Current Reality:**
- Conversations captured → PostgreSQL (status='pending_embedding')
- Background worker processes embeddings
- Completed embeddings stored in pgvector table
- Neo4j ChatSession nodes updated with embedding property

**Reference:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/06-DATA_FLOWS/CURRENT_PIPELINE.md`

---

## Planned Features (Not Yet Implemented)

### Vault Indexing → KG

**Status:** ⚡ PLANNED

**Original Intent:** When system stopped sending conversations directly to Vault, implement high-level summaries to Vault enabling:
- Search vault contents for conversational context
- Fetch full historical conversations from organizational datalake
- Link ideas together by following graph edges

**Current Reality:** Feature deferred due to numerous components arriving simultaneously. Core infrastructure hardened, reducing urgency.

**Future Direction:**
- Vault indexing via `vault_utils.py` upgrade (documented in `OmegaVault/.trash/TNP-HG-Phase-2-Workflow 1 (Obsidian-Linear) v2.md`)
- Integrate with semantic search on KG
- Provide cross-linking through Neo4j graph

**Reference Document:** `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/06-DATA_FLOWS/FUTURE_VAULT_FLOW.md`

**Architectural Decision Reference:** `OmegaVault/.trash/TNP-HG-Phase-2-Workflow 1 (Obsidian-Linear) v2.md`

---

## Component Coverage

**Primary Focus: Omega_KG_stable**

Capture server, lifecycle engine, Neo4j, PostgreSQL, task management, Linear sync, percolation

**Cross-References:**

- **InGest-LLM.as**: Vector ingestion microservice
  - See: `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/04-SERVICES/INGEST_LLM_AS.md`
  - Reference: `InGest-LLM.as/.github/copilot-instructions.md`

- **memos.MCP**: Memory Operating System
  - See: `OmegaVault/ApexSigma/development/projects/OmegaKG/governance/07-MIRMIR_PROTOCOL/MEMOS_MCP_TOOLS.md`
  - Reference: `memos.MCP/01_Overview/AGENTS.md` (comprehensive, 368 lines)

- **CortexBridge**: Integration layer (if needed)
  - See: `CortexBridge/README.md`

- **OmegaVault**: External vault storage references
  - Configuration: `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Configuration\`
  - Databases: `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Databases\`
  - Testing: `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Testing\`
  - Security: `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Security\`

---

## How to Use This Governance System

### Before Starting a Task

1. Identify task type (coding, testing, debugging, architecture)
2. Jump to relevant governance section (see "By Section" table above)
3. Read linked governance document for patterns and examples
4. Check code style from `02-CODING_STANDARDS/CODE_STYLE.md`
5. Retrieve existing context via memos.MCP if applicable

### During Task Execution

1. Follow code style from `02-CODING_STANDARDS/`
2. Use testing patterns from `03-TESTING/`
3. Reference service documentation when touching components
4. Record to memos.MCP after significant actions (see `07-MIRMIR_PROTOCOL/`)

### After Completing Task

1. Run quality gates: `poetry run pre-commit run --all-files`
2. Run relevant tests: `poetry run pytest`
3. If architectural decision made: record to memos.MCP
4. Update this file if patterns changed

---

## Existing Documentation References

### OmegaVault Library (Authoritative Source)

**Configuration & Setup:**
- 📄 `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Configuration\CONFIGURATION.md`
- 📄 `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Configuration\SETUP_COMPLETE.md`

**Databases:**
- 📄 `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Databases\Neo4j\NEO4J_SETUP.md`
- 📄 `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Databases\Postgres\`

**Testing:**
- 📄 `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Testing\PYTEST_GUIDE.md`
- 📄 `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Testing\COVERAGE_QUICKSTART.md`

**Security:**
- 📄 `d:\projects\OmegaKG\OmegaVault\ApexSigma\Development\Projects\OmegaKG\Security\ZERO_TRUST_QUICK_REFERENCE.md`

### Component-Specific AGENTS.md

**Primary Components:**
- 📄 `Omega_KG_stable/OmegaVault/ApexSigma/development/projects/OmegaKG/guidelines/agents.md` - Comprehensive agent guidance (84 lines)
- 📄 `memos.MCP/01_Overview/AGENTS.md` - memos.MCP server documentation (368 lines)

**Legacy Planning:**
- 📄 `OmegaVault/.trash/TNP-HG-Phase-2-Workflow 1 (Obsidian-Linear) v2.md` - Historical planning context

---

## Notes for Maintainers

- **Keep it current:** Governance docs = single source of truth, not aspirational
- **Code-verify:** Any claim about patterns must be verified against actual codebase
- **Be specific:** Reference exact files and line numbers where possible
- **Link intelligently:** Cross-reference related docs, not external websites
- **Mark status:** Use 📋 (pending), 🔄 (in progress), ✅ (complete), ⚡ (planned), ❌ (deprecated)
- **Update as we go:** This file tracks implementation progress

---

**Getting Started:**
1. Read relevant governance doc for your task (2-10 minutes)
2. Follow patterns, execute task (varies)
3. Record significant outcomes to memos.MCP if applicable

---

**This governance system is designed for continuous, transparent evolution.**

Questions or suggestions? Update this file with feedback.

---

## MCP Configuration (Claude Code Integration)

**Status**: ✅ **CONFIGURED** - memOS.MCP and Serena tools available via Model Context Protocol

### Quick Access
- **Setup Guide**: [`OmegaVault/ApexSigma/development/projects/memos.MCP/docs/configuration.md`](OmegaVault/ApexSigma/development/projects/memos.MCP/docs/configuration.md)
- **Quick Reference**: [`OmegaVault/ApexSigma/development/projects/memos.MCP/docs/reference.md`](OmegaVault/ApexSigma/development/projects/memos.MCP/docs/reference.md)
- **Setup Summary**: [`OmegaVault/ApexSigma/development/projects/OmegaKG/archive/reports/mcp_setup_complete.md`](OmegaVault/ApexSigma/development/projects/OmegaKG/archive/reports/mcp_setup_complete.md)
- **Verification**: Run `python scripts/maintenance/verify-mcp-config.py`

### Available MCP Tools

#### memOS.MCP Server (11 tools)
- **Intelligence**: `consult_mirmir`, `verify_implementation` (Mirmir Protocol)
- **Context**: `retrieve_context`, `get_concepts`, `get_constraints`
- **Memory**: `scratch_write`, `scratch_read`, `scratch_clear`, `set_working_memory`, `get_working_memory`
- **Learning**: `mark_significant`, `promote_memory`

#### Serena Server
- Semantic code navigation and manipulation tools

### Getting Started
1. **Start infrastructure**: `cd memos.MCP && .\start-memos.ps1`
2. **Verify setup**: `python scripts\verify_mcp_config.py`
3. **Ask Claude**: "What MCP tools are available?"
4. **Approve servers** when prompted (one-time)

### Configuration File
`.mcp.json` in workspace root defines MCP servers for Claude Code integration.

---

## Mimir Protocol & memOS Usage

The **Mimir Protocol** is the system's "immune system," enforcing architectural constraints and preventing regression. **ALL Agents must adhere to the following:**

### 1. Mandatory Agent Review (MAR)
Before executing *any* task that modifies core systems (`domain/linear`, `omega_kg`) or deletes files, you **MUST** consult the Codex.

**Tool:** `consult_mirmir(plan_text, intended_outcome, affected_entities)`
- **When:** Start of any refactor, deletion, or architectural change.
- **Why:** To check for "Immune Memory" (historical failures).
- **If REJECTED:** You must abandon the plan or modify it according to the verdict.

### 2. Implementation Verification
After generating a plan or code, use the verification tool to double-check against constraints.

**Tool:** `verify_implementation(plan_text, implementation_diff)`
- **When:** Before committing code.
- **Why:** Uses a secondary LLM (Qwen 2.5) to "peer review" your work against Mimir constraints.

### 3. Reflective Analysis
If you encounter a failure or bug during your session, you must add it to the Codex to "immunize" the system.

**Tool:** `promote_memory(content, tags=["codex", "failure"], metadata={"severity": "WARNING"})`
- **When:** After resolving an error.
- **Format:** "CONTEXT: [What happened]. ROOT CAUSE: [Why]. CONSTRAINT: [Rule to prevent recurrence]."

### 4. Mandatory Recording of Significant Work (PROPOSED: MCP-MEM-001)
**Status**: 📋 Proposed Constraint - Pending Infrastructure Activation

Agents MUST use memOS.MCP tools to record significant work when available:
- **Significant work includes**: Architectural decisions, infrastructure changes, bug fixes, integration configurations, failed approaches
- **Use `scratch_write()`** during complex work to trace reasoning
- **Use `mark_significant()`** after completing high-significance tasks
- **Use `promote_memory()`** to persist insights to knowledge base

**Rationale**: Born from irony of configuring MCP system without using it to record the configuration work itself. Demonstrates need for explicit constraint to ensure organizational learning.

**Full Proposal**: See [`OmegaVault/ApexSigma/development/projects/OmegaKG/governance/07-MIRMIR_PROTOCOL/CODEX_CONSTRAINT_PROPOSAL_MCP-MEM-001.md`](OmegaVault/ApexSigma/development/projects/OmegaKG/governance/07-MIRMIR_PROTOCOL/CODEX_CONSTRAINT_PROPOSAL_MCP-MEM-001.md)

**Mirmir Verdict**: ✅ APPROVED (risk_score: 0.0) - "Proceed with caution" (infrastructure needs activation)
