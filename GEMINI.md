# GEMINI.md

This file provides context to Gemini when working with the Soma ecosystem.

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

Soma is a biomorphic knowledge management system that bridges sensory capture (InGress) with long-term memory (Neo4j) through a metabolic digestion process (InGest).

### Component Map

1. **InGress (Senses)**: Receives raw signals (JSON/Text).
2. **Postgres (Raw Lake)**: Stores un-digested sensory data.
3. **InGest (Stomach)**: Processes signals through SimpleMem Stage 1.
4. **Redis (Nervous System)**: Ephemeral stream of knowledge digests.
5. **OmegaKG (Brain)**: Consumes digests and persists to Neo4j.
6. **memOS (Hands)**: MCP interface for agentic retrieval.

## Building and Running

### Executive Life-Support

Use the central orchestrator to manage the organism:

```powershell
python orchestrator.py
```

### End-to-End Verification

Always execute a "Meal Trace" after modifications:

```powershell
.\scripts\operations\trace-meal.ps1
```

## Development Conventions

* **Guidelines**: Strictly follow `AGENTS.md`.
* **Immune System**: Consult the Mirmir Protocol via `memOS.MCP`.
* **Encoding**: Always use `encoding="utf-8"`.
* **Type Safety**: Type hints are mandatory for all function signatures.

## Mimir Protocol (System Integrity)

Soma implements a "Digital Immune System" called the **Mimir Protocol**, accessed via `memOS.MCP`.

### Key Concepts

* **The Codex**: Historical record of failures and architectural constraints.
* **MAR (Mandatory Agent Review)**: Query the Codex (`consult_mirmir`) before critical actions.
* **Metabolization**: Convert failures into new Codex rules (`promote_memory`).

---

*Sanitized: 2026-01-28*
