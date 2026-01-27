# memOS.MCP Infrastructure Setup Guide

## Critical Dependencies

memOS.MCP requires three services to be running:

### 1. Redis (Port 6379)
**Purpose:** Ephemeral working memory and scratchpad storage

**Start Redis (Windows):**
```powershell
# Option A: Using Docker
docker run -d -p 6379:6379 --name memos-redis redis:7-alpine

# Option B: Using Windows Redis binary
# Download from: https://github.com/microsoftarchive/redis/releases
# Run: redis-server.exe
```

**Verify:**
```powershell
# Using redis-cli
redis-cli ping
# Should return: PONG

# Or using Python
python -c "import redis; r=redis.Redis(); print(r.ping())"
```

### 2. Ollama (Port 11434)
**Purpose:** Embedding generation using bge-m3 model

**Start Ollama (Windows):**
```powershell
# Option A: Install Ollama Desktop from https://ollama.com/download
# Then pull the required model:
ollama pull bge-m3

# Option B: Using Docker
docker run -d -p 11434:11434 --name memos-ollama ollama/ollama
docker exec memos-ollama ollama pull bge-m3
```

**Verify:**
```powershell
# Check service
curl http://localhost:11434/api/tags

# Test embedding
curl -X POST http://localhost:11434/api/embeddings `
  -H "Content-Type: application/json" `
  -d '{"model":"bge-m3","prompt":"test"}'
```

### 3. PostgreSQL with pgvector (Port 5800)
**Purpose:** Persistent vector storage

**Start PostgreSQL:**
```powershell
# Using Docker Compose (from memos.MCP directory)
cd d:\projects\OmegaKG\memos.MCP
docker-compose up -d postgres

# Or standalone Docker
docker run -d `
  -p 5800:5432 `
  --name memos-postgres `
  -e POSTGRES_USER=omega_user `
  -e POSTGRES_PASSWORD=your_password `
  -e POSTGRES_DB=omega_kg_stable `
  ankane/pgvector:latest
```

**Initialize Schema:**
```powershell
cd d:\projects\OmegaKG\memos.MCP
poetry run python -m scripts.init_db
```

## Quick Start (All Services)

**Option 1: Docker Compose (Recommended)**
```powershell
cd d:\projects\OmegaKG\memos.MCP

# Start all services
docker-compose up -d

# Verify all running
docker-compose ps

# View logs
docker-compose logs -f
```

**Option 2: Manual Start**
```powershell
# Terminal 1: Redis
docker run -d -p 6379:6379 --name memos-redis redis:7-alpine

# Terminal 2: Ollama
# (Install Ollama Desktop and ensure it's running)
ollama serve  # If not running as service

# Terminal 3: PostgreSQL
docker run -d -p 5800:5432 --name memos-postgres `
  -e POSTGRES_USER=omega_user `
  -e POSTGRES_PASSWORD=your_password `
  -e POSTGRES_DB=omega_kg_stable `
  ankane/pgvector:latest

# Terminal 4: memOS.MCP
cd d:\projects\OmegaKG\memos.MCP
poetry run python -m memos_mcp --sse
```

## Development Mode (Mock Services)

For testing without infrastructure dependencies:

```powershell
# Set environment variable to enable mock mode
$env:MEMOS_MOCK_MODE = "true"

# Start server
poetry run python -m memos_mcp --sse
```

Mock mode will:
- Use in-memory dictionary instead of Redis
- Return dummy embeddings instead of calling Ollama
- Use SQLite instead of PostgreSQL

## Environment Configuration

Create `.env` file in `memos.MCP/`:

```ini
# Redis (Ephemeral Memory)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

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

# Server Configuration
FASTMCP_SERVER_PORT=8768
FASTMCP_SERVER_HOST=0.0.0.0
FASTMCP_SERVER_TRANSPORT=sse
```

## Troubleshooting

### Error: "Connection refused" (Redis)
```powershell
# Check if Redis is running
docker ps | findstr redis

# Start Redis if not running
docker start memos-redis

# Or create new instance
docker run -d -p 6379:6379 --name memos-redis redis:7-alpine
```

### Error: "404 Not Found" (Ollama)
```powershell
# Check Ollama service
curl http://localhost:11434/api/tags

# If not running, start Ollama Desktop or:
ollama serve

# Ensure model is pulled
ollama pull bge-m3
ollama list  # Verify bge-m3 is present
```

### Error: "Connection refused" (PostgreSQL)
```powershell
# Check PostgreSQL container
docker ps | findstr postgres

# View logs
docker logs memos-postgres

# Restart if needed
docker restart memos-postgres
```

## Health Check

```powershell
# Check all services at once
poetry run python -c "
import asyncio
import redis
import httpx
import asyncpg

async def check():
    # Redis
    try:
        r = redis.Redis(host='localhost', port=6379)
        print(f'✅ Redis: {r.ping()}')
    except Exception as e:
        print(f'❌ Redis: {e}')
    
    # Ollama
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get('http://localhost:11434/api/tags')
            print(f'✅ Ollama: {resp.status_code}')
    except Exception as e:
        print(f'❌ Ollama: {e}')
    
    # PostgreSQL
    try:
        conn = await asyncpg.connect(
            host='localhost', port=5800,
            user='omega_user', password='your_password',
            database='omega_kg_stable'
        )
        await conn.close()
        print('✅ PostgreSQL: Connected')
    except Exception as e:
        print(f'❌ PostgreSQL: {e}')

asyncio.run(check())
"
```

## Production Checklist

- [ ] Redis running and accessible
- [ ] Ollama running with bge-m3 model pulled
- [ ] PostgreSQL running with pgvector extension
- [ ] Database schema initialized (`scripts/init_db.py`)
- [ ] `.env` file configured with secure credentials
- [ ] Neo4j running (for graph memory, if enabled)
- [ ] All services pass health check
- [ ] memOS.MCP starts without errors

## Next Steps

After infrastructure is running:
1. Start memOS.MCP: `poetry run python -m memos_mcp --sse`
2. Verify health endpoint: `curl http://localhost:8768/health`
3. Test MCP tools from Claude Desktop or VS Code
