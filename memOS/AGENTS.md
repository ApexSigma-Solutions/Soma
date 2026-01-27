# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build/Lint/Test Commands

```bash
# Install dependencies (Poetry-managed project)
poetry install

# Install with dev dependencies (includes ruff, mypy, pytest, pre-commit)
poetry install --with dev

# Run MCP server (defaults to SQLite)
python src/memos_mcp/server.py

# Or use FastMCP CLI
fastmcp run src/memos_mcp/server.py

# Lint & format with Ruff
poetry run ruff check .
poetry run ruff format .

# Type checking with mypy
poetry run mypy src/

# Run tests (pytest.ini sets pythonpath=src)
pytest
pytest -v  # Verbose output
pytest -k "test_store_memory"  # Run specific tests

# Pre-commit hooks (run before committing)
poetry run pre-commit run --all-files
poetry run pre-commit install  # Install git hooks
```

## Code Organization

```
src/memos_mcp/
├── server.py              # FastMCP entry point - registers tools/resources
├── config.py              # Pydantic Settings for environment config
├── logic.py               # MCP tool implementations (store_memory, retrieve_context, etc.)
├── models.py              # Pydantic request/response models
├── schemas.py             # Enums (MCPTier, MemoryTier) and memory schemas
├── prompts.py             # LLM prompts for various operations
└── database/
    ├── __init__.py        # Database factory: get_database()
    ├── base.py            # Abstract Database interface (8 methods)
    ├── sqlite.py          # SQLite implementation (default)
    ├── postgres.py        # PostgreSQL implementation (production)
    ├── neo4j.py           # Neo4j implementation (stub, not production-ready)
    ├── qdrant.py          # Vector search client with placeholder embeddings
    └── redis.py           # Working memory cache (optional)

tests/                     # Test suite (currently minimal - only __init__.py exists)
docs/                      # Documentation (API_REFERENCE, DATABASE_CONFIGURATION, DEPLOYMENT)
scripts/                   # Utility scripts (setup_test_databases, seed_tools, init_database)
```

## Code Style & Conventions

### Configuration
- **Settings pattern**: All config in [`src/memos_mcp/config.py`](src/memos_mcp/config.py:5) using Pydantic BaseSettings
- **Environment loading**: Loads from `.env` file, then env vars, then defaults
- **Validation**: [`check_passwords()`](src/memos_mcp/config.py:30) validates required passwords for postgres/neo4j
- **Key settings**: `MEMOS_DB_TYPE`, `fastmcp_server_port`, `memos_enable_tool_registry`, `memos_max_memory_size`

### Database Abstraction Pattern
**CRITICAL**: Never instantiate database backends directly. Always use the factory:

```python
# DON'T
from src.memos_mcp.database.postgres import PostgresDatabase
db = PostgresDatabase()

# DO
from src.memos_mcp.database import get_database
db = get_database()  # Respects MEMOS_DB_TYPE config
```

**Pattern**:
- Abstract interface: [`Database`](src/memos_mcp/database/base.py:4) with 8 required methods
- Thread-safe singleton: [`get_database()`](src/memos_mcp/database/__init__.py:12) uses double-checked locking
- New backends: Implement all abstract methods from [`base.py`](src/memos_mcp/database/base.py)

### MCP Tool Registration
Tools and resources are registered in [`server.py`](src/memos_mcp/server.py:1):

```python
mcp = FastMCP("MemOS Cognitive Server")

# Tools (callable operations)
mcp.tool(logic.store_memory)
mcp.tool(logic.retrieve_context)
mcp.tool(logic.register_tool)

# Resources (data endpoints with URI patterns)
mcp.resource("memory://{agent_id}/graph")(logic.memory_graph)
mcp.resource("memory/tools")(logic.tool_registry)
```

**Pattern**: Business logic lives in [`logic.py`](src/memos_mcp/logic.py:1), keep [`server.py`](src/memos_mcp/server.py:1) minimal for registration.

### SQLAlchemy ORM Pattern (PostgreSQL/SQLite)
```python
from contextlib import contextmanager

@contextmanager
def get_session(self) -> Session:
    session = self.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Usage**: Always use `with self.get_session()` for automatic commit/rollback.

### Naming Conventions
- **Tables**: Singular nouns (`Memory`, `RegisteredTool`)
- **Columns**: snake_case (`agent_id`, `memory_metadata`, `embedding_id`)
- **Models**: PascalCase in source files, table names explicit in `__tablename__`
- **Environment variables**: `MEMOS_` prefix for app settings, `POSTGRES_` / `NEO4J_` for database

## Code Style (Non-Obvious)

- **Database backend selection**: Set `MEMOS_DB_TYPE=sqlite|postgres|neo4j` in `.env` - default is `sqlite`
- **Qdrant is optional**: [`get_qdrant_client`](src/memos_mcp/database/qdrant.py) returns `None` if Qdrant unavailable; operations gracefully skip vector features
- **Testing mode**: Set `TESTING=1` env var to use [`SQLiteDatabase(db_path="test_memory.db")`](src/memos_mcp/database/__init__.py:18)
- **FastMCP entry point**: Server instance is `mcp` object in [`server.py`](src/memos_mcp/server.py:16), not a function
- **MCP tier mapping**: [`MCPTier`](src/memos_mcp/schemas.py:4) maps to memory tiers: `MCP_GEMINI/COPILOT/QWEN` → `PROCEDURAL (Tier2)`, `MCP_SYSTEM` → `SEMANTIC (Tier3)`
- **FastMCP config**: See [`fastmcp.json`](fastmcp.json) - uses SSE transport on port 8080 by default
- **pytest config**: [`pytest.ini`](pytest.ini) sets `pythonpath=src` - tests can import `memos_mcp` directly
- **Poetry lockfile**: Committed to version control for reproducible dependency resolution (despite .gitignore template)

## Testing Approach

**Current State**: Test suite is minimal - only `tests/__init__.py` exists, no actual tests written yet.

**When adding tests**:
- Use `pytest` with `pytest-asyncio` (already in dependencies)
- Test against SQLite for speed, PostgreSQL for production parity
- Mock Qdrant client for vector operations
- Set `TESTING=1` env var to use test database

**Test patterns to follow**:
```python
# Async test for MCP tools
import pytest
from memos_mcp.logic import store_memory

@pytest.mark.asyncio
async def test_store_memory():
    result = await store_memory(agent_id="test_agent", content="test memory")
    assert result["status"] == "success"
    assert "memory_id" in result
```

## Critical Patterns & Gotchas

### Database Patterns
- **Database singleton**: [`get_database()`](src/memos_mcp/database/__init__.py:12) uses double-checked locking for thread-safe singleton initialization
- **PostgreSQL sessions**: Always use context manager [`with self.get_session()`](src/memos_mcp/database/postgres.py:49) for automatic commit/rollback
- **Memory embedding linkage**: Qdrant point IDs are stored in PostgreSQL via [`update_memory_embedding_id()`](src/memos_mcp/database/base.py:18) - always update both stores together
- **JSON columns**: Use SQLAlchemy `JSON` type for `memory_metadata` and `tags` columns

### Vector Search Limitations
- **Placeholder embeddings**: [`generate_placeholder_embedding()`](src/memos_mcp/database/qdrant.py:241) uses MD5 hash - **NOT suitable for production semantic search**
- **To add real embeddings**: Replace placeholder with actual embedding model (e.g., sentence-transformers)
- **Qdrant is optional**: All operations must function without Qdrant - check `if get_qdrant_client:` before using

### Memory Tier Architecture
- **Tier 1 (Working)**: Redis cache (short-lived, TTL-based) - [`store_working_memory()`](src/memos_mcp/database/redis.py)
- **Tier 2 (Procedural)**: Database for tools/procedures - maps to `MCP_GEMINI/COPILOT/QWEN`
- **Tier 3 (Semantic)**: Long-term semantic memory with embeddings - maps to `MCP_SYSTEM`

### MCP Protocol
- **Tools vs Resources**: Tools are callable operations, Resources are data endpoints with URI patterns
- **Agent scoping**: Always include `agent_id` in memory operations for multi-tenant isolation
- **Tool registration**: Register capabilities for cross-agent discoverability via [`register_tool()`](src/memos_mcp/logic.py)

### Observability
- **Langfuse integration**: Available but pending activation - see docs/OBSERVABILITY.md
- **Logging**: Uses Python standard `logging` module with structured messages
- **Health check**: `/health` endpoint returns `{"status": "healthy", "service": "memos_mcp"}`

## Docker Deployment

### Single Service (Standalone)
```bash
docker-compose -f docker/docker-compose.yml up --build
```

### Unified Stack (Integration Testing)
```bash
docker-compose -f docker-compose.unified.yml up -d
```

Includes: PostgreSQL (5432), Qdrant (6333), Neo4j (7687), Redis (6379), Langfuse (3000)

**Docker specifics**:
- Base image: `python:3.11-slim`
- Uses `uv` for fast dependency installation
- Volumes: `/data/{sqlite,postgres,neo4j}` for persistence
- Health check: `/health` endpoint with 30s interval
- FastMCP entrypoint: `fastmcp run server.py` (SSE transport on port 8080)

### Environment Variables
Required environment variables in production:
- `MEMOS_DB_TYPE`: `sqlite|postgres|neo4j`
- `POSTGRES_PASSWORD`: Required when using PostgreSQL
- `NEO4J_PASSWORD`: Required when `MEMOS_ENABLE_GRAPH_MEMORY=true`

See [`docker/docker-compose.yml`](docker/docker-compose.yml:15) for full list.

## Database Schema

### memories table
```python
id: int (PK, auto-increment)
content: text (required)
agent_id: str (default: "default_agent")
memory_metadata: json (nullable)
embedding_id: str (nullable, links to Qdrant)
created_at: datetime (UTC)
updated_at: datetime (UTC, auto-update)
```

### registered_tools table
```python
id: int (PK, auto-increment)
name: str (unique, required)
description: text (required)
usage: text (required)
tags: json (nullable, list of strings)
created_at: datetime (UTC)
updated_at: datetime (UTC, auto-update)
```

## Pre-Commit Hooks

Configured in [`.pre-commit-config.yaml`](.pre-commit-config.yaml):
- **Trailing whitespace fixer**
- **End-of-file fixer**
- **YAML syntax checker**
- **Large file detector**
- **Ruff linting** (with `--fix` auto-fix)
- **Ruff formatting**
- **Poetry check** (validates pyproject.toml)

Install hooks: `poetry run pre-commit install`
Run all hooks: `poetry run pre-commit run --all-files`

## Common Patterns & Anti-Patterns

### ✅ Correct: Agent-scoped memory operations
```python
# Store with agent context
await store_memory(agent_id="agent_123", content="user prefers dark mode", metadata={"category": "preference"})

# Query within agent scope
results = await retrieve_context(agent_id="agent_123", query="what are user preferences?", top_k=5)
```

### ✅ Correct: Tool registration for discoverability
```python
# Register capabilities for other agents to discover
await register_tool(
    tool_name="web_scraper",
    description="Extract content from web pages",
    usage="Use when user provides URL to analyze",
    tags=["web", "content", "analysis"]
)
```

### ✅ Correct: Optional dependency handling
```python
try:
    from memos_mcp.database.qdrant import get_qdrant_client
except ImportError:
    logger.info("Qdrant is not available. Proceeding without Qdrant support.")
    get_qdrant_client = None

# Always check before using
if get_qdrant_client:
    qdrant_client = get_qdrant_client()
    # Use Qdrant
else:
    # Fallback behavior
```

### ❌ Avoid: Hardcoding database client instantiation
```python
# DON'T
from src.memos_mcp.database.postgres import PostgresDatabase
db = PostgresDatabase()

# DO
from src.memos_mcp.database import get_database
db = get_database()  # Respects MEMOS_DB_TYPE config
```

### ❌ Avoid: Bypassing database abstraction
```python
# DON'T - direct SQL in logic layer
db.session.execute("SELECT * FROM memories WHERE agent_id = ?", [agent_id])

# DO - use abstraction methods
db.get_memories_by_ids(memory_ids)
```

### ❌ Avoid: Forgetting to update both stores
```python
# DON'T - only update Qdrant
qdrant_client.store_embedding(...)

# DO - update both Qdrant and PostgreSQL
point_id = qdrant_client.store_embedding(...)
db.update_memory_embedding_id(memory_id, point_id)
```

## Integration Points

### Standalone Mode
Server runs independently with SQLite, no external dependencies required.

### Unified Stack Mode ([docker-compose.unified.yml](docker-compose.unified.yml))
- **PostgreSQL** (port 5432): Production memory storage
- **Qdrant** (port 6333): Vector similarity search
- **Neo4j** (bolt://localhost:7687): Graph relationships (stub implementation)
- **Redis** (port 6379): Working memory cache
- **Langfuse** (port 3000): Observability (pending integration)

Services communicate via Docker network `unified_net` with predictable DNS resolution.

## Troubleshooting

### Database Connection Issues
```bash
# Verify database is running
docker-compose -f docker/docker-compose.yml ps

# Check logs
docker-compose -f docker/docker-compose.yml logs memos-mcp

# Test connection
curl http://localhost:8080/health
```

### Import Errors
- Ensure `pytest.ini` has `pythonpath = src`
- Run `poetry install` for dependency installation

### Poetry vs pip
- Project uses Poetry for dependency management (pyproject.toml, poetry.lock)
- Use `poetry install` NOT `pip install -e .`
- Poetry lockfile is committed to version control

### Qdrant Unavailable
- Check if Qdrant is running: `docker ps | grep qdrant`
- Verify `QDRANT_HOST` and `QDRANT_PORT` env vars
- Server will function without Qdrant (no vector search)
