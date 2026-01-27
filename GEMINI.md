# OmegaKG Ecosystem Context

> [!CAUTION]
> **WINDOWS DOCKER NETWORKING WARNING**
> Due to Windows Docker networking limitations, we use a **Hybrid Architecture**:
> *   **DATA LAYER**: Redis, PostgreSQL (pgvector), and Neo4j run in **Docker Containers**.
> *   **LOGIC LAYER**: OmegaKG, memOS.MCP, and InGest-LLM run **natively on the Host**.
> *   **DO NOT** attempt to containerize the application logic services.
> *   **ALWAYS** ensure containers map ports to `localhost` for host access.

# OmegaKG Project Context

## Project Overview

OmegaKG is a Neo4j-powered knowledge management system that bridges Obsidian vaults, Linear tasks, and Git commits. It facilitates intelligent knowledge capture and task lifecycle management using a dual-agent architecture (Kilo Code & Roo Code).

The system consists of three main components:

1. **Omega_KG (Core):** The central nervous system handling conversation capture, task lifecycle, and knowledge graph persistence.
2. **memos.MCP (Bridge):** A Model Context Protocol server that connects the knowledge graph ("Brain") to the IDE/Agents ("Hands"), providing context retrieval and working memory.
3. **InGest-LLM.as (Ingestion):** A microservice for ingesting data into the ecosystem.

## Key Technologies

**Languages:**
Python 3.12.10 (Backend), JavaScript/TypeScript (Chrome Extension).

**Frameworks:**
FastAPI (`omega-capture`), FastMCP (`memos-mcp`).

**Databases:**

* **Neo4j:** Knowledge graph relationships.
* **PostgreSQL:** Vector storage and event logging.
* **Redis:** Ephemeral working memory.
* **SQLite:** Development/Test databases.

**Infrastructure:** Docker Compose, Poetry (Dependency Management).

**Tools:** MkDocs, Ruff, Mypy, Pytest.

## Architecture & Services

### 1. Omega_KG (Core)

* **Path:** `./Omega_KG_stable/`
* **Function:** Captures AI conversations via Chrome extension, syncs with Linear/Obsidian, and manages task states.
* **Key Files:**
  * `capture_server.py`: FastAPI entry point (Port 8765).
  * `lifecycle.py`: Task state machine.
  * `linear_sync.py`: Linear integration.

### 2. memos.MCP (The Bridge / memOS)

* **Path:** `./memos.MCP/`
* **Function:** A "Memory Operating System" providing agents with tiered context retrieval, working memory, and architectural governance.
* **Tiered Memory Architecture:**
  * **Tier 1 (Working):** Ephemeral Redis-backed cache for session-specific context (`set_working_memory`, `scratch_write`).
  * **Tier 2 (Procedural):** Database of tools, procedures, and failure constraints (`get_constraints`, `register_tool`).
  * **Tier 3 (Semantic):** Long-term knowledge graph (Neo4j) and vector store (PostgreSQL) for deep context retrieval (`retrieve_context`).
* **Key Files:**
  * `src/memos_mcp/server.py`: FastMCP server entry point (Port 8768).
  * `src/memos_mcp/logic.py`: Core tool implementations and memory management logic.

### 3. InGest-LLM.as (The Digestor)

* **Path:** `./InGest-LLM.as/`
* **Function:** Ingests external data, promoted memories, and working experiences into the ecosystem.
* **Key Files:**
  * `src/ingest_llm_as/main.py`: Application entry point.

## Building and Running

### Prerequisites

* Python 3.12.10
* Poetry
* Docker & Docker Compose

### Common Commands

**Setup & Installation:**

```bash
# Root: Install dependencies for all projects
cd Omega_KG_stable && poetry install --with dev
cd ../memos.MCP && poetry install
cd ../InGest-LLM.as && poetry install
```

**Docker (Recommended for full stack):**

```bash
# Start all services (Omega Capture + memos.MCP + InGest-LLM)
.\start_ecosystem.ps1 -Persistent -ShowConsole
```

**Testing:**

```bash
# Omega_KG
cd Omega_KG_stable && poetry run pytest

# memos.MCP
cd memos.MCP && poetry run pytest

# Script categories available:
poetry run python scripts/database/verify-phase2-readiness.py
poetry run python scripts/testing/run-phase2-audit.ps1
poetry run python scripts/maintenance/repair-mcp-configuration.py
```

## Development Conventions

* **Agents Guidelines:** Strictly follow `AGENTS.md`. Record significant discoveries to `memos.MCP`.
* **Mirmir Protocol:** Mandatory for high-risk changes.
* **Encoding:** Always use `encoding="utf-8"` for file operations.
* **Type Hints:** Mandatory for all signatures.

## Mimir Protocol (System Integrity)

OmegaKG implements a "Digital Immune System" called the **Mimir Protocol**, which agents access via `memOS.MCP`.

### Key Concepts

* **The Codex:** A repository of "Anti-Bodies" (constraints derived from past failures).
* **MAR (Mandatory Agent Review):** Agents must query the Codex (`consult_mirmir`) before critical actions.
* **Metabolization:** Failures must be converted into new Codex rules (`promote_memory`) to prevent recurrence.

### memOS Toolset

Use these tools via the `memos` MCP server:

* **Context & Memory:** `retrieve_context`, `get_working_memory`, `set_working_memory`, `mark_significant`.
* **Governance:** `consult_mirmir`, `verify_implementation`, `get_constraints`.
* **Reasoning Trace:** `scratch_write`, `scratch_read`, `scratch_clear`.
* **Discovery:** `get_concepts`.
