# OmegaKG Ecosystem

## Overview
OmegaKG is a sophisticated knowledge graph integration system combining Neo4j, PostgreSQL (pgvector), and LLM-based ingestion services to create a comprehensive memory and operation system for the ApexSigma architecture.

## Repository Structure

```
d:/projects/OmegaKG/
├── CortexBridge/            # React/Vite Frontend Dashboard
├── InGest-LLM.as/          # Vector Ingestion Microservice (Python/FastAPI)
├── memos.MCP/              # Model Context Protocol Server (Python)
├── Omega_KG_stable/        # Core Knowledge Graph Service (Python/FastAPI)
├── OmegaVault/             # Central Knowledge Base (Obsidian Vault)
│   └── ApexSigma/
│       └── development/
│           └── projects/   # Consolidated Project Documentation
│               ├── OmegaKG/
│               ├── memos.MCP/
│               └── InGest-LLM/
├── scripts/                # Operational Scripts
│   ├── database/
│   ├── maintenance/
│   ├── operations/
│   ├── testing/
│   └── utilities/
└── tests/                  # Integration Tests
```

## Quick Start

### Prerequisites
- Python 3.12+
- Poetry 2.0+
- Docker Desktop (for Redis, Neo4j, Postgres)
- PowerShell 7+

### Setup
1. **Install Dependencies**:
   ```powershell
   poetry install
   ```

2. **Start Infrastructure**:
   ```powershell
   ./scripts/operations/launch-unified.ps1
   ```

3. **Verify Status**:
   ```powershell
   python scripts/maintenance/verify-mcp-config.py
   ```

## Documentation

Primary documentation is centrally located in the Vault:
- **Governance & Guidelines**: [`OmegaVault/ApexSigma/development/projects/OmegaKG/governance/`](OmegaVault/ApexSigma/development/projects/OmegaKG/governance/)
- **Architecture**: [`OmegaVault/ApexSigma/development/projects/OmegaKG/docs/architecture/`](OmegaVault/ApexSigma/development/projects/OmegaKG/docs/architecture/)
- **Operations**: [`OmegaVault/ApexSigma/development/projects/OmegaKG/docs/ops/`](OmegaVault/ApexSigma/development/projects/OmegaKG/docs/ops/)
- **Agent Guidelines**: [`OmegaVault/ApexSigma/development/projects/OmegaKG/guidelines/agents.md`](OmegaVault/ApexSigma/development/projects/OmegaKG/guidelines/agents.md)

### Key Guides
- **Script Reference**: [`scripts/SCRIPTS_REFERENCE.md`](scripts/SCRIPTS_REFERENCE.md)
- **MCP Configuration**: [`OmegaVault/ApexSigma/development/projects/memos.MCP/docs/configuration.md`](OmegaVault/ApexSigma/development/projects/memos.MCP/docs/configuration.md)
- **Data Flow**: [`OmegaVault/ApexSigma/development/projects/OmegaKG/docs/architecture/dataflow.md`](OmegaVault/ApexSigma/development/projects/OmegaKG/docs/architecture/dataflow.md)

## Development Workflow

We use a strict **Poetry-based workflow**.
- All Python commands must be run via `poetry run <command>`.
- Use `scripts/operations/launch-unified.ps1` to start services.
- Consult `agents.md` before starting new tasks.

## Legacy & Archives
Old documentation and reports are archived in:
- `OmegaVault/ApexSigma/development/projects/OmegaKG/archive/`

---
*Sanitized and Reorganized: 2026-01-15*
