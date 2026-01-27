# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# OmegaKG Project Context

> [!CAUTION]
> **WINDOWS DOCKER NETWORKING WARNING**
> Due to Windows Docker networking limitations, we use a **Hybrid Architecture**:
> *   **DATA LAYER**: Redis, PostgreSQL (pgvector), and Neo4j run in **Docker Containers**.
> *   **LOGIC LAYER**: OmegaKG, memOS.MCP, and InGest-LLM run **natively on the Host**.
> *   **DO NOT** attempt to containerize the application logic services.
> *   **ALWAYS** ensure containers map ports to `localhost` for host access.

## Project Overview

**For detailed patterns and governance docs, see `AGENTS.md`**

OmegaKG is a Neo4j-powered knowledge management system that captures AI conversations from browser extensions, syncs with Linear tasks, and tracks implementation through Git commits. It features a FastAPI capture server, Chrome extension, Neo4j graph database, and Obsidian vault integration.

## Core System Components

### 1. Capture Server (`capture_server.py`)
- **Purpose**: FastAPI server that receives conversations from Chrome extension
- **Port**: 8765
- **Endpoints**:
  - `POST /capture` - Receives AI conversations
  - `GET /health` - Health check
  - `POST /webhook/linear` - Linear webhook receiver
- **Started via**: Task Scheduler at Windows login (for stable)
- **Ngrok Integration**: Automatically starts ngrok tunnel if `ENABLE_NGROK=true` in `.env`

### 2. Chrome Extension
- **Location**: `Omega_KG_stable/chrome-extension/`
- **Files**:
  - `background.js` - Service worker, handles retry logic
  - `content.js` - Injects into pages, extracts messages
  - `manifest.json` - Permissions and configuration
- **Supported Sites**: ChatGPT, Claude, Gemini, Perplexity, DeepSeek, Qwen, etc.

### 3. Database Layer
- **Neo4j** (Primary) - Graph database for relationships
  - Port 7687
  - Stores: Sessions, Decisions, Tasks, Commits, Relationships
- **PostgreSQL (pgvector)** - Event storage and vector embeddings
  - Port 5433
  - Stores: Events, Sessions, Audit logs, Vector embeddings

### 4. Linear Integration
- **File**: `linear_sync.py`
- **Purpose**: Bidirectional sync between Linear issues and Obsidian notes
- **Webhook**: `POST /webhook/linear` endpoint
- **Requires**: Ngrok tunnel for local development

## Common Development Commands

### Setup
```bash
# Install dependencies
poetry install --with dev --with docs

# Configure environment
cp .env.example .env
# Edit .env with NEO4J_URI, NEO4J_PASSWORD, OBSIDIAN_VAULT_PATH, etc.

# Verify configuration
poetry run python -c "from omega_kg.settings import settings; print('✓ Settings loaded')"
```

### Running the Application
```bash
# Start capture server (primary method)
poetry run capture-server
# OR
python -m omega_kg.capture_server

# Start with ngrok tunnel (for webhook testing)
# Set ENABLE_NGROK=true in .env first, then:
poetry run capture-server

# Task lifecycle management
poetry run python -m omega_kg.lifecycle --dry-run
poetry run python -m omega_kg.lifecycle

# CLI commands
poetry run omega lifecycle --help
poetry run omega stats
poetry run omega sync
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Testing
```bash
# All tests
poetry run pytest

# Fast tests only (skip Neo4j)
poetry run pytest -m "not requires_neo4j"

# Specific test file
poetry run pytest tests/test_lifecycle.py -v

# With coverage
poetry run pytest --cov=omega_kg --cov-report=html

# By markers
poetry run pytest -m unit
poetry run pytest -m slow
poetry run pytest -m requires_neo4j
```

### Code Quality
```bash
# Linting
poetry run ruff check .
poetry run ruff check . --fix  # Auto-fix

# Type checking
poetry run mypy omega_kg/

# Formatting
poetry run ruff format .
poetry run ruff format . --check  # Check without changing

# Security scanning
poetry run bandit -c pyproject.toml -ll -r .

# Pre-commit hooks
poetry run pre-commit install
poetry run pre-commit run --all-files
```

### Documentation
```bash
# Serve docs locally
poetry run mkdocs serve
# View at http://localhost:8000
```

### Chrome Extension
```powershell
# Load extension (PowerShell)
# Note: Load manually via chrome://extensions
# 1. Enable Developer mode
# 2. Click "Load unpacked"
# 3. Select chrome-extension/ folder
```

# Manual:
# 1. Open chrome://extensions
# 2. Enable Developer mode
# 3. Click "Load unpacked"
# 4. Select chrome-extension/ folder
```

## Architecture & Code Structure

### Key Python Modules

| Module | Purpose |
|--------|---------|
| `settings.py` | Pydantic settings from `.env`, Bitwarden integration |
| `capture_server.py` | FastAPI app, routes, startup logic, ngrok integration |
| `lifecycle.py` | Automated task state transitions |
| `linear_sync.py` | Linear webhook processing, issue sync logic |
| `percolation.py` | Extract insights from markdown into Neo4j graph |
| `neo4j_schema.py` | Graph schema initialization |
| `cli.py` | Command-line interface |
| `vector_store.py` | Vector embeddings for semantic search |
| `database/graph.py` | AsyncGraphDriver for Neo4j (async context managers required) |
| `database/session.py` | Async SQLAlchemy session management |
| `workers/embedding_worker.py` | Background embedding processing (polls every 10s) |
| `domain/linear/*` | Linear webhook, mapper, graph_writer modules |
| `routers/*` | FastAPI route handlers (capture, github_receiver, linear_receiver, etc.) |
| `ngrok_tunnel.py` | Ngrok tunnel management |
| `intelligence/codex.py` | Codex integration |

### Neo4j Data Model
```
ChatSession -[:CONTAINS]-> Decision
Task -[:IMPLEMENTS]-> Decision
Commit -[:IMPLEMENTS]-> Task
Session -[:CONTAINS_COMMIT]-> Commit
Task -[:TRACKED_BY]-> LinearIssue
Decision -[:CAPTURED_IN]-> ChatSession
```

### Configuration Management

**Settings Load Order**:
1. Bitwarden SDK (if `BWS_ACCESS_TOKEN` set)
2. Environment variables
3. `.env` file
4. Defaults in `settings.py`

**Key Settings** (`.env`):
```ini
OMEGA_ENV=dev|stable|temp  # Environment isolation
OBSIDIAN_VAULT_PATH=./vault|D:/projects/omegavault.as
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=...
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5800
POSTGRES_DB=omega_kg_stable
LINEAR_API_KEY=...
LINEAR_WEBHOOK_SECRET=...
ENABLE_NGROK=true|false  # For webhook testing
NGROK_API_KEY=...  # Optional, for persistent URLs
```

## Development Workflow

### Making Changes
```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes and test
poetry run pytest
poetry run ruff check .
poetry run mypy omega_kg/

# 3. Pre-commit checks
poetry run pre-commit run --all-files

# 4. Commit and push
git add .
git commit -m "feat: description"
git push origin feature/my-feature

# 5. Open PR to alpha branch
```

### Testing Guidelines
- **Unit tests**: Fast, no external dependencies (`-m unit`)
- **Integration tests**: Require services (`-m requires_neo4j`)
- **Slow tests**: Long-running (`-m slow`)
- **Coverage**: Currently ~47%, target >80%

## Ngrok Integration for Webhooks

### Automatic Startup
When `ENABLE_NGROK=true` in `.env`, the capture server automatically:
1. Starts ngrok tunnel on port 8765
2. Logs public URL: `https://abc-def-123.ngrok.io`
3. Provides webhook URL: `https://abc-def-123.ngrok.io/webhook/linear`

### Manual Usage
```bash
# Terminal 1: Start server
poetry run capture-server

# Terminal 2: Start ngrok
ngrok http 8765

# Copy ngrok URL and configure Linear webhook
```

### Linear Webhook Configuration
- **URL**: `https://<ngrok-url>/webhook/linear`
- **Secret**: `LINEAR_WEBHOOK_SECRET` from `.env`
- **Events**: Issue Created, Updated, Deleted

## Security & Best Practices

### Zero Trust with Bitwarden
- Production secrets managed via Bitwarden SDK
- Access tokens in `.env` (never commit)
- Secret UUIDs in environment variables
- Fallback to local `.env` values

### Windows Task Scheduler
- Capture server starts at login
- Runs: `python -m omega_kg.capture_server`
- Ngrok starts automatically if enabled
- Paths must be updated if project moves

## Common Troubleshooting

### Extension Not Capturing
```bash
# 1. Verify capture server running
curl http://localhost:8765/health

# 2. Reload extension
chrome://extensions → Find Omega_KG → Reload

# 3. Check extension logs
chrome://extensions → Omega_KG → Service worker → Inspect

# 4. Verify selectors
# Open DevTools on supported site → Console
# Look for [Omega_KG] log messages
```

### Neo4j Connection Failed
```bash
# 1. Check Neo4j is running
# Neo4j Desktop or docker-compose up -d neo4j

# 2. Verify credentials
grep NEO4J .env

# 3. Test connection
poetry run python -c "from neo4j import GraphDatabase; ..."
```

### Webhook Not Working
```bash
# 1. Enable ngrok
# Edit .env: ENABLE_NGROK=true

# 2. Start server (ngrok starts automatically)
poetry run capture-server

# 3. Copy ngrok URL from logs
# 4. Update Linear webhook URL
# 5. Test by creating issue in Linear
```

### Pre-commit Failures
```bash
# Auto-fix
poetry run ruff check . --fix
poetry run ruff format .

# Run all checks
poetry run pre-commit run --all-files
```

## Important Files

### Configuration
- `.env` - Environment variables (NEVER commit real secrets)
- `.env.example` - Template for new setups
- `pyproject.toml` - Dependencies and scripts
- `docker-compose.yml` - Service definitions

### Source Code
- `omega_kg/settings.py` - Configuration
- `omega_kg/capture_server.py` - FastAPI app
- `omega_kg/linear_sync.py` - Linear integration
- `omega_kg/lifecycle.py` - Task automation
- `Omega_KG_stable/chrome-extension/` - Browser extension

### Documentation
- **Governance**: `docs/GOVERNANCE/` - Active development documentation
- **Vault**: `OmegaVault/ApexSigma/development/projects/OmegaKG/` - Consolidated documentation
- **AGENTS.md**: Entry point for detailed patterns and governance docs

## Getting Help

- **API Docs**: http://localhost:8765/docs (when server running)
- **Neo4j Browser**: http://localhost:7474/browser/
- **Project Docs**: `docs/` directory
- **Health Check**: `GET http://localhost:8765/health`

## Critical Patterns

**See `AGENTS.md` for detailed patterns and governance documentation.**

### Neo4j Async Context Managers (MANDATORY)
Always use async context managers for Neo4j sessions to prevent connection leaks:
```python
async with graph_driver.session() as session:
    result = await session.run("MATCH (n) RETURN n")
    record = await result.single()
```

### UTF-8 Encoding Required
All file I/O must specify `encoding="utf-8"`:
```python
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
```

### Background Task Timing
- APScheduler: runs every 5 minutes for batch operations
- Embedding worker: polls every 10 seconds for pending embeddings

## Key Principles for Claude

1. **Check AGENTS.md first** - Contains detailed patterns and governance docs
2. **Use async context managers** - Required for all Neo4j sessions to prevent leaks
3. **Specify UTF-8 encoding** - All file I/O must use `encoding="utf-8"`
4. **Configuration is critical** - Always check `.env` settings first
5. **Ngrok is optional** - Only needed for webhook testing
6. **Test before suggesting changes** - Run `poetry run pytest`
7. **Check docs first** - Many answers in `docs/` directory
