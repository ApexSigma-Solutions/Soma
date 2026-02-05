# Soma: The Distributed Organism

## Overview

Soma is a decentralized, biomorphic knowledge ecosystem designed for lifelong learning and autonomous task execution. It consolidates vision (Senses), metabolism (InGest), reasoning (Brain), and motor control (Hands) into a single, cohesive organism.

## Repository Structure

```text
d:/projects/Soma/
├── InGress/                 # 🖐️ Senses: Signal Capture (FastAPI)
├── InGest/                  # 🫃 Stomach: Metabolism & SimpleMem (Python)
├── OmegaKG/                 # 🧠 Brain: Knowledge Graph & Persistence (Python)
├── memOS/                   # ✋ Hands: Model Context Protocol (MCP)
├── Cortex/                  # 👁️ Vison: Dashboard Hub (React/Vite)
├── OmegaVault/              # 📚 Memory: Central Knowledge Base (Obsidian)
├── scripts/                 # 🛠️ Operations & Maintenance
└── orchestrator.py          # 🫀 Executive: Organism Life-Support
```

## Quick Start

### Prerequisites

- Python 3.12.10
- Poetry or .venv (Manual)
- Docker Desktop (Neo4j, Postgres, Redis)
- PowerShell 7+

### Life-Support (Startup)

1. **Assembling the Organs**:

   ```powershell
   # Start all services via the executive orchestrator
   python orchestrator.py
   ```

2. **Verifying Health**:

   ```powershell
   # Execute a Meal Trace (E2E Verification)
   .\scripts\operations\trace-meal.ps1
   ```

## Documentation

Primary governance and context are maintained in the Vault:

- **Architecture**: [`OmegaVault/ApexSigma/Development/Projects/Soma/architecture/`](OmegaVault/ApexSigma/Development/Projects/Soma/architecture/)
- **Operations**: [`OmegaVault/ApexSigma/Development/Projects/Soma/operations/`](OmegaVault/ApexSigma/Development/Projects/Soma/operations/)
- **Legacy Archives**: [`OmegaVault/ApexSigma/Development/Projects/Soma/archive/`](OmegaVault/ApexSigma/Development/Projects/Soma/archive/)

### Key Reference

- **Agent Guidelines**: [`AGENTS.md`](./AGENTS.md)
- **Script Reference**: [`scripts/SCRIPTS_REFERENCE.md`](./scripts/SCRIPTS_REFERENCE.md)
- **Startup Guide**: [`OmegaVault/ApexSigma/Development/Projects/Soma/operations/startup-guide.md`](OmegaVault/ApexSigma/Development/Projects/Soma/operations/startup-guide.md)
- **Meal Trace Guide**: [`OmegaVault/ApexSigma/Development/Projects/Soma/operations/meal-trace-guide.md`](OmegaVault/ApexSigma/Development/Projects/Soma/operations/meal-trace-guide.md)

## Development Workflow

Soma uses a **Native Organism Workflow**:

- **Executive**: Use `orchestrator.py` to manage service lifecycles.
- **Verification**: All changes MUST pass a `trace-meal.ps1` verification.
- **Memory**: Record architectural decisions to `memOS.MCP` via `promote_memory`.

## Legacy & Archives

Historical OmegaKG documentation is archived in:

- `archive/legacy/`
- `OmegaVault/ApexSigma/development/projects/Soma/archive/`

---

**Sanitized and Reorganized**: 2026-01-28 (Soma Genesis)
