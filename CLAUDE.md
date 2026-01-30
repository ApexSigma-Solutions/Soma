# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in the Soma repository.

## Soma Organism Context

> [!CAUTION]
> **WINDOWS DOCKER NETWORKING WARNING**
> Due to Windows Docker networking limitations, we use a **Hybrid Architecture**:
>
> * DATA LAYER: Redis, PostgreSQL (pgvector), and Neo4j run in **Docker Containers**.
> * LOGIC LAYER: InGress, InGest, OmegaKG, and memOS run **natively on the Host**.
> * **DO NOT** attempt to containerize the application logic services.
> * **ALWAYS** ensure containers map ports to `localhost` for host access.

## Project Overview

**For detailed patterns and governance docs, see `AGENTS.md`**

Soma is a biomorphic knowledge management system. It captures signals via InGress, digests them in the InGest stomach, persists them to the Neo4j Brain via OmegaKG, and acts through memOS hands.

## Core System Components

### 1. InGress (Senses)

* **Purpose**: FastAPI sensory layer for signal capture.
* **Port**: 8000
* **Started via**: `orchestrator.py`

### 2. InGest (Stomach)

* **Purpose**: SimpleMem Stage 1 metabolism (Entropy, Coreference, Temporal).
* **Function**: Polls Postgres `raw_lake`, publishes to Redis `soma_working_memory`.
* **Started via**: `orchestrator.py`

### 3. OmegaKG (Brain)

* **Purpose**: Neo4j persistence and knowledge graph management.
* **Function**: Consumes from Redis stream, MERGEs AtomicFact nodes.
* **Started via**: `orchestrator.py`

### 4. memOS (Hands)

* **Purpose**: FastMCP 2.0 server for agentic interaction.
* **Port**: 8768
* **Started via**: `orchestrator.py`

## Common Development Commands

### Startup (Executive)

```powershell
# Start the entire organism
python orchestrator.py
```

### Verification (Meal Trace)

```powershell
# Execute End-to-End trace
.\scripts\operations\trace-meal.ps1
```

### Quality Gates

```bash
# Linting & Formatting
pre-commit run --all-files
```

## Architecture & Principles

1. **Thin Senses**: InGress should stay minimal.
2. **Heavy Stomach**: InGest handles the complex digestion logic.
3. **Graph Brain**: Neo4j is the source of truth for relationships.
4. **Mimir Immune System**: Always check `consult_mirmir` before core changes.

## Critical Patterns

* **Async Neo4j**: Always use `async with graph_driver.session()`.
* **UTF-8**: Always specify `encoding="utf-8"` in file I/O.
* **Host DNS**: Connecting from host to Docker? Use `localhost`.

---

*Sanitized: 2026-01-28*
