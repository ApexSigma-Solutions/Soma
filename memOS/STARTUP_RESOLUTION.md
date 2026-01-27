# memOS.MCP Startup Issue - Resolution Summary

## Problem Diagnosis

The memOS.MCP server was failing to start with three critical errors:

### 1. Redis Connection Error (Port 6379)
```
Error 22 connecting to localhost:6379. The remote computer refused the network connection.
```
**Root Cause:** Redis service not running. Required for ephemeral working memory and scratchpad functionality.

### 2. Ollama Embeddings Error (Port 11434)
```
Client error '404 Not Found' for url 'http://localhost:11434/api/embeddings'
```
**Root Cause:** Ollama service not running or bge-m3 model not pulled. Required for generating 1024-dimensional embeddings.

### 3. PostgreSQL Connection (Port 5800)
**Root Cause:** PostgreSQL with pgvector extension not running. Required for persistent vector storage.

## Solution Implemented

### Created Infrastructure Files

1. **`INFRASTRUCTURE_SETUP.md`** - Comprehensive setup guide with:
   - Individual service installation instructions
   - Quick start commands for all services
   - Environment configuration templates
   - Troubleshooting guide
   - Health check procedures

2. **`docker-compose.yml`** - Complete infrastructure stack:
   ```yaml
   services:
     redis:        # Ephemeral memory (port 6379)
     postgres:     # Vector storage (port 5800)
     ollama:       # Embeddings (port 11434)
   ```
   - Includes automatic model download for bge-m3
   - Health checks for all services
   - Persistent volume configuration
   - Network isolation

3. **`docker/init-db.sql`** - PostgreSQL initialization:
   - Creates `memos` schema
   - Sets up `memories` and `memory_audit` tables
   - Enables pgvector extension
   - Creates indexes for vector similarity search
   - Grants permissions to omega_user

4. **`start-memos.ps1`** - Windows PowerShell automation script:
   ```powershell
   .\start-memos.ps1          # Start all services
   .\start-memos.ps1 -Status  # Check service health
   .\start-memos.ps1 -Stop    # Stop all services
   .\start-memos.ps1 -Logs    # Follow logs
   .\start-memos.ps1 -Clean   # Remove all data
   ```

5. **`scripts/health_check.py`** - Python health verification:
   - Tests Redis connectivity
   - Verifies Ollama API and bge-m3 model
   - Checks PostgreSQL, pgvector, and memos schema
   - Provides actionable feedback

### Updated Documentation

6. **`README.md`** - Added Quick Start section with three options:
   - **Option 1:** Automated setup with `start-memos.ps1`
   - **Option 2:** Manual Docker Compose
   - **Option 3:** Development mock mode (no infrastructure)

## How to Use

### Quick Start (Recommended)

```powershell
# Navigate to memos.MCP directory
cd d:\projects\OmegaKG\memos.MCP

# Start all infrastructure services
.\start-memos.ps1

# Verify health
poetry run python scripts\health_check.py

# Initialize database schema (first time only)
poetry run python scripts\init_db.py

# Start memOS.MCP server
poetry run python -m memos_mcp --sse
```

### Service Management

```powershell
# Check status
.\start-memos.ps1 -Status

# View logs
.\start-memos.ps1 -Logs

# Stop services
.\start-memos.ps1 -Stop

# Clean all data (WARNING: destructive)
.\start-memos.ps1 -Clean
```

### Manual Docker Commands

```powershell
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Service Verification

After starting services, verify each component:

### Redis
```powershell
# Test connection
docker exec memos-redis redis-cli ping
# Expected: PONG
```

### Ollama
```powershell
# Check models
curl http://localhost:11434/api/tags

# Test embedding
curl -X POST http://localhost:11434/api/embeddings `
  -H "Content-Type: application/json" `
  -d '{"model":"bge-m3","prompt":"test"}'
```

### PostgreSQL
```powershell
# Connect to database
docker exec -it memos-postgres psql -U omega_user -d omega_kg_stable

# In psql:
\dt memos.*           # List tables
\d memos.memories     # Describe memories table
SELECT version();     # Check PostgreSQL version
```

## Environment Configuration

Create `.env` file in `memos.MCP/`:

```ini
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSION=1024

# PostgreSQL
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

## Next Steps

1. **Start Infrastructure:**
   ```powershell
   .\start-memos.ps1
   ```

2. **Verify Health:**
   ```powershell
   poetry run python scripts\health_check.py
   ```

3. **Initialize Database (first time only):**
   ```powershell
   poetry run python scripts\init_db.py
   ```

4. **Start memOS.MCP:**
   ```powershell
   poetry run python -m memos_mcp --sse
   ```

5. **Test Connection:**
   ```powershell
   curl http://localhost:8768/health
   ```

## Development Mode (No Infrastructure)

For testing without services:

```powershell
$env:MEMOS_MOCK_MODE = "true"
poetry run python -m memos_mcp --sse
```

Mock mode uses:
- In-memory dictionary instead of Redis
- Dummy embeddings instead of Ollama
- SQLite instead of PostgreSQL

## Architecture Reference

```
┌─────────────────────────────────────────────────────────────┐
│                  memOS.MCP Infrastructure                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Redis     │  │   Ollama     │  │  PostgreSQL  │      │
│  │  (port 6379) │  │ (port 11434) │  │  (port 5800) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         │     Ephemeral   │   Embeddings    │  Persistent   │
│         │      Memory     │   (bge-m3)      │   Vectors     │
│         └─────────────────┴─────────────────┘               │
│                          │                                  │
│                   ┌──────▼───────┐                          │
│                   │ memOS.MCP    │                          │
│                   │ (port 8768)  │                          │
│                   └──────────────┘                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Files Created

1. `/memos.MCP/INFRASTRUCTURE_SETUP.md` - Detailed setup guide
2. `/memos.MCP/docker-compose.yml` - Infrastructure orchestration
3. `/memos.MCP/docker/init-db.sql` - Database initialization
4. `/memos.MCP/start-memos.ps1` - Windows automation script
5. `/memos.MCP/scripts/health_check.py` - Service verification
6. `/memos.MCP/README.md` - Updated with Quick Start

## Troubleshooting

See [INFRASTRUCTURE_SETUP.md](d:\projects\OmegaKG\memos.MCP\INFRASTRUCTURE_SETUP.md) for detailed troubleshooting steps.

Common issues:
- Docker not installed/running
- Ports already in use
- Models not pulled (bge-m3)
- Database schema not initialized
- Incorrect credentials in .env
