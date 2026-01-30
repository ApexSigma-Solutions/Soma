# Scripts Reference

This document provides a comprehensive reference for all scripts in the Soma ecosystem, organized by functional category.

## Directory Structure

```text
scripts/
├── database/              # Database operations and migrations
├── infrastructure/        # Service recovery and indexing
├── maintenance/           # System diagnostics and configuration
├── operations/            # E2E verification and legacy startup
├── testing/               # Specialized logic and auth tests
├── utilities/             # Route checking and password testing
└── archive/               # Versioned and legacy scripts (do not use)
```

## Executive Control

### orchestrator.py (Root)
**Purpose**: Primary entry point to start the entire Soma organism.
**Usage**: `python orchestrator.py`
**Description**: Spawns visible telemetry consoles for Senses, Stomach, Brain, and Hands.

---

## Operations & Verification

### trace-meal.ps1
**Purpose**: Execute an End-to-End "Terminal Ghost" signal trace.
**Usage**: `./scripts/operations/trace-meal.ps1`
**Description**: Injects a signal via InGress and verifies its path through InGest to Neo4j.

### verify-meal-trace.py
**Purpose**: Backend logic for meal trace verification.
**Usage**: `python scripts/operations/verify-meal-trace.py`
**Description**: Programmatic verification of the pipeline.

---

## Infrastructure & Recovery

### force-reset-launch.ps1
**Purpose**: Hard reset of all Docker containers and Host logic.
**Usage**: `./scripts/infrastructure/force-reset-launch.ps1`

### soma-vector-indexes.cypher
**Purpose**: Initialize Neo4j vector indexes for Qwen3 embeddings.
**Usage**: Applied via `cypher-shell` or Neo4j Browser.

---

## Maintenance & Diagnostics

### verify-mcp-config.py
**Purpose**: Verify and debug MCP configuration and connectivity.
**Usage**: `python scripts/maintenance/verify-mcp-config.py`

### repair-mcp.py
**Purpose**: Interactive repair tool for `.mcp.json` and tool registration.
**Usage**: `python scripts/maintenance/repair-mcp.py`

---

## Utilities

### check-routes.py
**Purpose**: Verify InGress and InGest endpoint availability.
**Usage**: `python scripts/utilities/check-routes.py`

### test-passwords.py
**Purpose**: Brute-force check for Neo4j/Postgres credentials against .env.
**Usage**: `python scripts/utilities/test-passwords.py`

---

**Last Updated**: 2026-01-28 (Soma Genesis)
**Status**: Active