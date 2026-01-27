# memos.MCP

The **Conceptual Bridge** between the OmegaKG Brain and the IDE Hands.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for full system model.

```
       All Sources → InGest-LLM (single digestor)
                           ↓
              PostgreSQL + Neo4j (persistent brain)
                     ↙         ↘
            memOS.MCP            OmegaVault
               ↓                    ↓
              IDE               Linear/GitHub
```

## Features

### 🧠 Context Retrieval (Brain → Hands)
- **`retrieve_context`**: Semantic search from PGVector
- **`get_concepts`**: Traversal of Neo4j knowledge graph
- **`get_constraints`**: Rule enforcement from Mimir

### 🤲 Working Memory (Hands)
- **Redis Integration**: Fast, ephemeral storage
- **Scratchpad**: Trace reasoning steps (`scratch_write`/`read`)
- **Session Context**: Manage working state (`set`/`get_working_memory`)

### 🎓 Learning (Hands → Brain)
- **`mark_significant`**: Flag experiences for promotion
- **`promote_memory`**: Send to InGest-LLM for permanent storage
- **Auto-promotion**: Significance threshold triggers automatic ingestion

## Quick Start

### Prerequisites

memOS.MCP requires three infrastructure services:
- **Redis** (port 6379) - Ephemeral working memory
- **Ollama** (port 11434) - Embeddings with bge-m3 model
- **PostgreSQL** (port 5800) - Persistent vector storage

### Option 1: Automated Setup (Recommended)

```powershell
# Windows: Start all infrastructure services
cd memos.MCP
.\start-memos.ps1

# Verify services are healthy
poetry run python scripts\health_check.py

# Initialize database schema
poetry run python scripts\init_db.py

# Start memOS.MCP server
poetry run python -m memos_mcp --sse
```

### Option 2: Manual Setup

```powershell
# Start services with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# Initialize database
poetry run python scripts\init_db.py

# Start server
poetry run python -m memos_mcp --sse
```

### Option 3: Development Mode (No Infrastructure)

```powershell
# Set mock mode (uses in-memory storage)
$env:MEMOS_MOCK_MODE = "true"

# Start server
poetry run python -m memos_mcp --sse
```

For detailed setup instructions, see [INFRASTRUCTURE_SETUP.md](INFRASTRUCTURE_SETUP.md)

### Configuration

Create `.env` file:

```ini
# Redis (Ephemeral Memory)
REDIS_HOST=localhost
REDIS_PORT=6379

# Ollama (Embeddings)
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSION=1024

# PostgreSQL (Persistent Storage)
POSTGRES_HOST=localhost
POSTGRES_PORT=5800
POSTGRES_DB=omega_kg_stable
POSTGRES_USER=omega_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_SCHEMA=memos

# Server
FASTMCP_SERVER_PORT=8768
FASTMCP_SERVER_HOST=0.0.0.0
FASTMCP_SERVER_TRANSPORT=sse
```

## Tools

| Tool | Category | Usage |
|------|----------|-------|
| `retrieve_context` | Query | `retrieve_context(query="auth flow", limit=5)` |
| `get_concepts` | Query | `get_concepts(concept_id="UserAuth", depth=2)` |
| `scratch_write` | Memory | `scratch_write(content="Planning schema...")` |
| `promote_memory` | Learn | `promote_memory(memory_id="123")` |

## Components

- **FastMCP**: Server framework
- **PGVectorStore**: Async vector retrieval
- **RedisMemoryClient**: Ephemeral storage manager
- **Logic Layer**: Integrates databases and enforces constraints

## Documentation

- [OmegaVault/ApexSigma/Development/Projects/memos.MCP](../OmegaVault/ApexSigma/Development/Projects/memos.MCP) - Centralized Documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System Design
- [BUILD.md](BUILD.md) - Build Guide
