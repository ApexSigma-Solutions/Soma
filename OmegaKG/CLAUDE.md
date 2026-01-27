# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Project Setup
```bash
# Install dependencies
poetry install --with dev

# Create environment config
cp .env.example .env
# Edit .env with OBSIDIAN_VAULT_PATH, NEO4J_PASSWORD, POSTGRES_PASSWORD, etc.

# Start databases
docker compose up -d neo4j-db postgres-db
```

### Development Server
```bash
# Start capture server (port 8765)
poetry run capture-server

# Run lifecycle checks (task state management)
poetry run python -m omega_kg.lifecycle --dry-run

# Run CLI commands
poetry run omega --help
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test types
poetry run pytest -m "unit"                    # Unit tests only
poetry run pytest -m "integration"             # Integration tests
poetry run pytest -m "requires_neo4j"          # Neo4j required

# Run with coverage
poetry run pytest --cov=omega_kg --cov-report=xml

# Run specific test file
poetry run pytest tests/test_capture.py -v
```

### Code Quality
```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run all quality checks
poetry run pre-commit run --all-files

# Individual tools
poetry run ruff check .                        # Lint
poetry run ruff check --fix .                  # Lint + auto-fix
poetry run ruff format .                       # Format code
poetry run mypy omega_kg                       # Type checking
poetry run bandit -c pyproject.toml -ll -r .   # Security linting
```

## Architecture Overview

### Core System Flow
Chrome Extension → Capture Server (FastAPI) → Obsidian Vault + Neo4j + PostgreSQL

### Key Architectural Patterns
- **Dual Database Strategy**: PostgreSQL for events/vectors + Neo4j for graph relationships
- **Async Everything**: Async/await throughout (FastAPI, SQLAlchemy, Neo4j, asyncpg)
- **Write-Behind Pattern**: Immediate capture, async embedding generation
- **Zero-Trust Security**: Bitwarden SDK integration with fallback to environment variables
- **Task Lifecycle Automation**: Auto-state transitions with APScheduler (Draft → Ready → Active → Blocked → Completed → Archived)

### Core Components

**Capture Server** (`capture_server.py`):
- FastAPI application (port 8765) with lifespan management
- Receives conversations from Chrome extension via `POST /capture`
- Saves to Obsidian vault, creates Neo4j graph relationships
- Background scheduler for task lifecycle management (every 5 minutes)
- Embedding worker initialization

**Chrome Extension** (`chrome-extension/`):
- Manifest V3 extension
- Captures conversations from supported AI platforms
- Supported: Claude, ChatGPT, Gemini, Perplexity, DeepSeek, Mistral, Qwen
- Sends data to capture server

**Database Layer** (`database/`):
- **PostgreSQL** (port 5433): Event storage, vector embeddings (pgvector)
- **Neo4j** (ports 7474/7687): Graph relationships (Sessions → Decisions → Tasks → Commits)

**Domain Models** (`domain/linear/`):
- Pydantic models for Linear webhook processing
- Data mapping and processing logic
- Graph writer for Neo4j relationships

### Configuration Priority
1. **Bitwarden Secrets** (if `BWS_ACCESS_TOKEN` set)
2. **Environment Variables** (`.env`)
3. **Defaults** (in `settings.py`)

### Graph Schema (Neo4j)
- `Session` → contains → `Decision`
- `Decision` → becomes → `Task`
- `Task` → implemented by → `Commit`
- `Session` ↔ related_to ↔ `Session`

### Background Workers
- **Embedding Worker**: Polls PostgreSQL for pending embeddings every 10 seconds
- **Lifecycle Scheduler**: Runs every 5 minutes, automates task state transitions

## Key Files
- **`pyproject.toml`** - Dependencies, scripts, test config
- **`docker-compose.yml`** - Database services (Neo4j, PostgreSQL)
- **`.env.example`** - Complete environment template
- **`pytest.ini`** - Test markers and configuration
- **`.pre-commit-config.yaml`** - Code quality hooks

## Port Reference
| Service | Port | Access |
|---------|------|--------|
| Capture Server | 8765 | http://localhost:8765 |
| Neo4j Browser | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | Database connection |
| PostgreSQL | 5433 | Database connection |

## Testing Architecture
- Test markers: `unit`, `integration`, `slow`, `requires_neo4j`, `requires_postgres`
- Testcontainers provides Neo4j 5.x + Postgres pgvector for integration tests
- Current coverage: ~46% (81 tests passing)