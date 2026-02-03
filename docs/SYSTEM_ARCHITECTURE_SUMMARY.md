# Soma System Architecture Summary

**Version:** 2.0  
**Last Updated:** 2026-01-31  
**Status:** All Services Operational

---

## Executive Summary

Soma is a biomorphic knowledge management system that processes sensory data through a pipeline modeled after human cognition. The architecture follows an organic metaphor:

- **Senses (InGress)** - Captures raw signals from external sources
- **Stomach (InGest)** - Digests and compresses information via SimpleMem
- **Nervous System (Redis)** - Routes signals between organs
- **Brain (OmegaKG)** - Persists knowledge to Neo4j graph database
- **Hands (memOS)** - Provides AI agent tools for memory and retrieval
- **Cortex (UI)** - Dashboard for monitoring and control

---

## System Architecture Diagram

```
                                    SOMA ECOSYSTEM
    ================================================================================
    
    EXTERNAL SOURCES                           CORTEX (Dashboard)
    +-----------------+                        +------------------------+
    | Obsidian        |                        | React 19 + TypeScript  |
    | GitHub Webhooks |                        | Vite Dev Server        |
    | Chrome Extension|                        | Port: 5173             |
    | Terminal Ghost  |                        +------------------------+
    | Manual/Agent    |                                   |
    +-----------------+                                   | HTTP/SSE
            |                                             v
            | HTTP POST                    +-----------------------------+
            v                              |      API Gateway (Proxy)    |
    +------------------+                   +-----------------------------+
    |    INGRESS       |                              |
    |  (The Senses)    |<-----------------------------+
    |  Port: 8000      |
    |  FastAPI/Uvicorn |
    +------------------+
            |
            | INSERT INTO raw_lake
            v
    +------------------+
    |   POSTGRES       |
    | (Sensory Lake)   |
    | Port: 6000       |
    | pgvector enabled |
    +------------------+
            |
            | Poll unprocessed records
            v
    +------------------+
    |    INGEST        |
    |  (The Stomach)   |
    |  Dagster UI: 3000|
    |  SimpleMem Stage1|
    +------------------+
            |
            | XADD soma_working_memory
            v
    +------------------+
    |     REDIS        |
    | (Nervous System) |
    | Port: 6380       |
    | Streams + Cache  |
    +------------------+
            |
            | XREADGROUP consumer
            v
    +------------------+
    |    OMEGAKG       |
    |  (The Brain)     |
    |  Consumer Mode   |
    |  Port: N/A       |
    +------------------+
            |
            | MERGE AtomicFact
            v
    +------------------+
    |     NEO4J        |
    | (Knowledge Graph)|
    | Bolt: 7687       |
    | Browser: 7474    |
    +------------------+
            ^
            | Read-only queries
            |
    +------------------+
    |     MEMOS        |
    |  (The Hands)     |
    |  Port: 8768      |
    |  FastMCP 2.x SSE |
    +------------------+
            ^
            |
    +------------------+
    | Claude Desktop   |
    | AI Agents (MCP)  |
    +------------------+
```

---

## Service Registry

### 1. InGress (The Senses)

**Purpose:** Lightweight sensory layer that captures raw data and buffers it to PostgreSQL.

| Property | Value |
|----------|-------|
| Port | 8000 |
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL (raw_lake table) |
| Auth | X-API-Key header |
| Start Command | `poetry run uvicorn soma_ingress.main:app --host 0.0.0.0 --port 8000` |

#### API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Basic health check |
| `/api/v1/system/vitals` | GET | X-API-Key | CPU, RAM, Disk telemetry |
| `/api/v1/vault/sync` | POST | X-API-Key | Obsidian vault file sync |
| `/api/v1/webhook/github` | POST | None | GitHub webhook receiver |
| `/api/v1/webhook/linear` | POST | None | Linear webhook receiver |
| `/api/v1/chrome/capture` | POST | X-API-Key | Chrome extension captures |
| `/api/v1/terminal/ghost` | POST | X-API-Key | Terminal command logging |
| `/api/v1/manual/ingest` | POST | X-API-Key | Manual/agent signal injection |
| `/api/v1/telemetry/stream` | GET | None | SSE stream of Redis events |

#### Request/Response Schemas

**Manual Ingest Request:**
```json
{
  "source": "manual|obsidian|github|chrome|terminal",
  "event_type": "agent_thought|file_mod|push|web_capture|command_log",
  "payload": {
    "content": "Signal content here",
    "timestamp": "2026-01-31T12:00:00Z",
    "metadata": {}
  }
}
```

**Response:**
```json
{
  "status": "captured",
  "ref": "uuid-of-raw-lake-record"
}
```

---

### 2. InGest (The Stomach)

**Purpose:** Metabolic processing via SimpleMem Stage 1 compression. Polls raw_lake, applies semantic compression, and emits to Redis stream.

| Property | Value |
|----------|-------|
| Dagster UI Port | 3000 |
| Framework | Dagster + asyncpg |
| Input | PostgreSQL raw_lake table |
| Output | Redis soma_working_memory stream |
| Start Command | `poetry run python ingest/raw_lake_poller_v2.py` |

#### SimpleMem Stage 1 Pipeline

```
raw_lake record
       |
       v
+------------------+
| 1. Entropy Gate  |  Filter H < 0.35 (low information)
+------------------+
       |
       v
+------------------+
| 2. Coreference   |  Replace pronouns with entity names
|    Resolution    |  (spaCy + coreferee)
+------------------+
       |
       v
+------------------+
| 3. Temporal      |  Convert "yesterday" to ISO-8601
|    Anchoring     |  (dateparser)
+------------------+
       |
       v
+------------------+
| 4. Atomic Fact   |  Synthesize Knowledge Digest
|    Synthesis     |
+------------------+
       |
       v
Redis XADD soma_working_memory
```

#### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_PG_DSN` | `postgresql://...localhost:6000/soma_sensory_lake` | Postgres connection |
| `SOMA_REDIS_URL` | `redis://localhost:6380/0` | Redis connection |
| `STOMACH_POLL_INTERVAL` | `5` | Seconds between polls |
| `STOMACH_BATCH_SIZE` | `10` | Records per batch |
| `SIMPLEMEM_ENTROPY_THRESHOLD` | `0.35` | Minimum entropy to pass gate |

#### Knowledge Digest Schema (Redis Payload)

```json
{
  "source_id": "uuid-from-raw-lake",
  "source": "obsidian|github|chrome|terminal|manual",
  "event_type": "file_mod|push|web_capture|agent_thought",
  "text": "Resolved and anchored text content",
  "metadata": {
    "original_entropy": 0.72,
    "source": "terminal",
    "event_type": "command_log",
    "pipeline_version": "simplemem-1.0"
  },
  "compressed_at": "2026-01-31T12:00:00+00:00"
}
```

---

### 3. OmegaKG (The Brain)

**Purpose:** Redis stream consumer that vectorizes Knowledge Digests and persists them to Neo4j as AtomicFact nodes.

| Property | Value |
|----------|-------|
| Port | None (consumer mode) |
| Framework | asyncio + neo4j-python |
| Input | Redis soma_working_memory stream |
| Output | Neo4j AtomicFact nodes |
| Consumer Group | `omegakg_brain` |
| Start Command | `poetry run python -m omega_kg.consumer` |

#### Consumer Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMA_REDIS_URL` | `redis://localhost:6380/0` | Redis connection |
| `SOMA_WORKING_MEMORY_STREAM` | `soma_working_memory` | Stream name |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | Required | Neo4j password |
| `EMBED_BASE_URL` | `http://localhost:12434` | Embedding API (Docker Model Runner) |
| `EMBED_MODEL` | `ai/qwen3-embedding:0.6B-F16` | Embedding model |

#### Neo4j AtomicFact Schema

```cypher
(:AtomicFact {
  text_hash: "sha256-prefix-16-chars",
  text: "Resolved fact text",
  embedding: [768-dim float vector],
  source_id: "uuid-from-raw-lake",
  source: "terminal|obsidian|...",
  metadata: "JSON string",
  created_at: datetime(),
  processed_at: datetime()
})
```

#### Guardian Router API (via FastAPI, if enabled)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/guardian/health` | GET | None | Guardian health check |
| `/guardian/validate` | POST | None | Validate against Codex |
| `/guardian/validate/hash` | POST | X-Soma-Key | Hash-based poison pill check |
| `/guardian/codex/log` | POST | X-Soma-Key | Log toxic artifact to Codex |
| `/guardian/commit` | POST | X-Soma-Key | Commit knowledge to Neo4j |
| `/guardian/store_embedding` | POST | X-Soma-Key | Store embedding for node |

---

### 4. memOS (The Hands)

**Purpose:** MCP server providing AI agents with memory tools, context retrieval, and Soma ecosystem integration.

| Property | Value |
|----------|-------|
| Port | 8768 |
| Framework | FastMCP 2.x + Uvicorn |
| Transport | SSE (HTTP) or stdio |
| Start Command | `poetry run python -m memos_mcp` |

#### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Memory statistics |
| `/memory/{tier}/store` | POST | Store memory by tier |
| `/mirmir/consult` | POST | Query Mirmir intelligence |
| `/pulse/emit` | POST | Emit pulse event |
| `/pulse/stream` | GET (SSE) | Stream pulse events |
| `/sse` | GET | MCP SSE transport |
| `/messages` | POST | MCP message handler |

#### MCP Tools

**Intelligence Layer (Brain):**

| Tool | Parameters | Description |
|------|------------|-------------|
| `consult_mirmir` | `plan_text`, `intended_outcome` | Query Mirmir for plan validation |
| `verify_implementation` | `code`, `requirements` | Verify code against requirements |

**Context Retrieval:**

| Tool | Parameters | Description |
|------|------------|-------------|
| `retrieve_context` | `query`, `limit` | Semantic search across memory |
| `get_concepts` | `domain` | Get domain concepts |
| `get_constraints` | `context` | Get applicable constraints |

**Working Memory (Redis):**

| Tool | Parameters | Description |
|------|------------|-------------|
| `scratch_write` | `session_id`, `content`, `metadata` | Write to scratchpad |
| `scratch_read` | `session_id`, `last_n` | Read recent scratchpad entries |
| `scratch_clear` | `session_id` | Clear scratchpad |
| `set_working_memory` | `session_id`, `key`, `value` | Set working memory value |
| `get_working_memory` | `session_id`, `key` | Get working memory value |

**Learning (Promotion):**

| Tool | Parameters | Description |
|------|------------|-------------|
| `mark_significant` | `session_id`, `content`, `significance`, `reason` | Mark experience for promotion |
| `promote_memory` | `session_id`, `memory_id` | Promote to long-term storage |

**Soma Integration:**

| Tool | Parameters | Description |
|------|------------|-------------|
| `ingest_signal` | `source`, `event_type`, `payload` | Push signal to InGress |
| `query_brain` | `cypher`, `limit` | Read-only Neo4j query |
| `promote_to_codex` | `constraint_type`, `rule`, `context`, `severity` | Promote constraint to Codex |

---

### 5. Cortex (Dashboard UI)

**Purpose:** React dashboard for monitoring and controlling the Soma ecosystem.

| Property | Value |
|----------|-------|
| Port | 5173 (dev) |
| Framework | React 19 + TypeScript + Vite |
| State | Zustand stores |
| Styling | Tailwind CSS |
| Start Command | `npm run dev` |

#### Routes (Hash-based)

| Hash | Component | Description |
|------|-----------|-------------|
| `#dashboard` | Dashboard | Overview with widgets |
| `#omega` | CaptureControl | Data capture interface |
| `#ingest` | IngestControl | Ingestion pipeline control |
| `#memos` | MemosControl | Memory management |
| `#cortex` | CortexBridge | Neural telemetry viewer |
| `#settings` | SettingsPage | System settings |

#### API Clients

| Client | Base URL | Target Port | Description |
|--------|----------|-------------|-------------|
| `omegaClient` | `/api/omega` | 8765 | OmegaKG Guardian API |
| `ingestClient` | `/api/ingest` | 8766 | InGest API |
| `memosClient` | `/api/memos` | 8768 | memOS API |
| `ingressClient` | `/api/ingress` | 8000 | InGress API |

#### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `VITE_API_OMEGA_URL` | `http://127.0.0.1:8765` | OmegaKG endpoint |
| `VITE_API_INGEST_URL` | `http://127.0.0.1:8766` | InGest endpoint |
| `VITE_API_MEMOS_URL` | `http://127.0.0.1:8768` | memOS endpoint |

---

## Infrastructure Services

### PostgreSQL (Sensory Lake)

| Property | Value |
|----------|-------|
| Container | `apexsigma.postgres.soma` |
| Image | `pgvector/pgvector:pg16` |
| Port | 6000 (mapped from 5432) |
| Database | `omega_kg_stable`, `soma_sensory_lake` |
| User | `omega_user` |
| Extensions | pgvector |

#### Key Tables

**raw_lake (InGress buffer):**
```sql
CREATE TABLE raw_lake (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  payload JSONB NOT NULL,
  client_ip VARCHAR(45),
  ingested_at TIMESTAMP DEFAULT NOW(),
  processed BOOLEAN DEFAULT FALSE,
  processed_at TIMESTAMP,
  failed BOOLEAN DEFAULT FALSE,
  retry_count INTEGER DEFAULT 0,
  last_error TEXT
);
```

---

### Neo4j (Knowledge Graph)

| Property | Value |
|----------|-------|
| Container | `apexsigma.neo4j.soma` |
| Image | `neo4j:5-community` |
| Bolt Port | 7687 |
| Browser Port | 7474 |
| User | `neo4j` |
| Plugins | APOC, Graph Data Science |

#### Node Labels

| Label | Description |
|-------|-------------|
| `AtomicFact` | Digested knowledge units from SimpleMem |
| `MemoryAtom` | Root nodes for committed knowledge |
| `Task` | Task nodes |
| `Constraint` | Codex constraint rules |
| `Concept` | Domain concepts |
| `File` | File references |

#### Indexes

```cypher
CREATE INDEX fact_text_hash FOR (f:AtomicFact) ON (f.text_hash);
CREATE INDEX fact_source_id FOR (f:AtomicFact) ON (f.source_id);
CREATE VECTOR INDEX fact_embedding FOR (f:AtomicFact) ON (f.embedding);
```

---

### Redis (Nervous System)

| Property | Value |
|----------|-------|
| Container | `apexsigma.redis.soma` |
| Image | `redis:7-alpine` |
| Port | 6380 (mapped from 6379) |
| Persistence | AOF (appendonly yes) |

#### Streams

| Stream | Consumer Group | Description |
|--------|----------------|-------------|
| `soma_working_memory` | `omegakg_brain` | Main digestion pipeline |
| `soma_working_memory:dlq` | N/A | Dead letter queue |
| `memos_pulse` | N/A | Pulse events for dashboard |

#### Key Patterns

| Pattern | Description |
|---------|-------------|
| `scratch:{session_id}` | Scratchpad entries (LIST) |
| `working:{session_id}` | Working memory (HASH) |
| `pending:{session_id}` | Pending memories (LIST) |

---

## Data Flow Diagrams

### E2E Signal Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SIGNAL INGESTION FLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

   External Source              InGress                    PostgreSQL
   ┌─────────────┐         ┌─────────────┐            ┌─────────────────┐
   │ Chrome Ext  │──POST──▶│ /api/v1/    │──INSERT───▶│    raw_lake     │
   │ Terminal    │         │ chrome/     │            │                 │
   │ GitHub      │         │ capture     │            │ id, source,     │
   │ Manual      │         │             │            │ event_type,     │
   └─────────────┘         └─────────────┘            │ payload, ...    │
                                                      └────────┬────────┘
                                                               │
                                                          Poll │ every 5s
                                                               ▼
                           ┌─────────────────────────────────────────┐
                           │              INGEST (Stomach)           │
                           │                                         │
                           │  1. Entropy Gate (H >= 0.35)           │
                           │  2. Coreference Resolution              │
                           │  3. Temporal Anchoring                  │
                           │  4. Atomic Fact Synthesis               │
                           │                                         │
                           └────────────────┬────────────────────────┘
                                            │
                                       XADD │ soma_working_memory
                                            ▼
                           ┌─────────────────────────────────────────┐
                           │              REDIS (Nervous System)     │
                           │                                         │
                           │  Stream: soma_working_memory            │
                           │  Consumer Group: omegakg_brain          │
                           │                                         │
                           └────────────────┬────────────────────────┘
                                            │
                                  XREADGROUP│ blocking
                                            ▼
                           ┌─────────────────────────────────────────┐
                           │              OMEGAKG (Brain)            │
                           │                                         │
                           │  1. Parse Knowledge Digest              │
                           │  2. Generate 768-dim Embedding          │
                           │  3. MERGE AtomicFact to Neo4j           │
                           │  4. XACK message                        │
                           │                                         │
                           └────────────────┬────────────────────────┘
                                            │
                                       MERGE│ AtomicFact
                                            ▼
                           ┌─────────────────────────────────────────┐
                           │              NEO4J (Knowledge Graph)    │
                           │                                         │
                           │  (:AtomicFact {                         │
                           │    text, embedding, source_id, ...      │
                           │  })                                     │
                           │                                         │
                           └─────────────────────────────────────────┘
```

### Agent Memory Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT MEMORY FLOW (MCP)                           │
└─────────────────────────────────────────────────────────────────────────────┘

   Claude Desktop              memOS                      Backend Services
   ┌─────────────┐         ┌─────────────┐            
   │   Agent     │──MCP───▶│ FastMCP SSE │            
   │             │         │ Port 8768   │            
   └─────────────┘         └──────┬──────┘            
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
   ┌───────────┐          ┌───────────┐          ┌───────────────┐
   │ scratch_  │          │ query_    │          │ ingest_signal │
   │ write     │          │ brain     │          │               │
   └─────┬─────┘          └─────┬─────┘          └───────┬───────┘
         │                      │                        │
         ▼                      ▼                        ▼
   ┌───────────┐          ┌───────────┐          ┌───────────────┐
   │   REDIS   │          │   NEO4J   │          │   INGRESS     │
   │ scratch:  │          │ Read-only │          │ /api/v1/      │
   │ {session} │          │ Cypher    │          │ manual/ingest │
   └───────────┘          └───────────┘          └───────────────┘
```

---

## Security Model

### Authentication Matrix

| Service | Endpoint Type | Auth Method | Header |
|---------|---------------|-------------|--------|
| InGress | Public webhooks | None | - |
| InGress | Authenticated | API Key | `X-API-Key` |
| OmegaKG Guardian | Internal | Soma Key | `X-Soma-Key` |
| memOS | MCP Tools | None (local) | - |
| memOS | HTTP Endpoints | Bearer Token | `Authorization` |
| Cortex | API Calls | Bearer Token | `Authorization` |

### Environment Variables (Secrets)

| Variable | Service | Description |
|----------|---------|-------------|
| `SOMA_INGRESS_KEY` | InGress | API key for authenticated endpoints |
| `SOMA_INTERNAL_KEY` | OmegaKG, InGest | Inter-service auth key |
| `NEO4J_PASSWORD` | OmegaKG, memOS | Neo4j database password |
| `POSTGRES_PASSWORD` | All | PostgreSQL password |

---

## Network Configuration

### Docker Network

| Property | Value |
|----------|-------|
| Network Name | `apexsigma.net` |
| Driver | bridge |
| Subnet | `172.20.0.0/16` |

### Port Mapping Summary

| Service | Internal Port | External Port | Protocol |
|---------|---------------|---------------|----------|
| InGress | 8000 | 8000 | HTTP |
| InGest (Dagster UI) | 3000 | 3000 | HTTP |
| memOS | 8768 | 8768 | HTTP/SSE |
| PostgreSQL | 5432 | 6000 | PostgreSQL |
| Neo4j Browser | 7474 | 7474 | HTTP |
| Neo4j Bolt | 7687 | 7687 | Bolt |
| Redis | 6379 | 6380 | Redis |
| Cortex (dev) | 5173 | 5173 | HTTP |

---

## Startup Procedures

### Recommended Startup Order

```powershell
# 1. Start Docker infrastructure
docker start apexsigma.postgres.soma apexsigma.neo4j.soma apexsigma.redis.soma

# 2. Wait for health checks (30 seconds for Neo4j)

# 3. Start application services (with SSL workaround)
$env:CURL_CA_BUNDLE=''; $env:SSL_CERT_FILE=''; $env:REQUESTS_CA_BUNDLE=''

# 4. InGress (Senses)
cd InGress
poetry run uvicorn soma_ingress.main:app --host 0.0.0.0 --port 8000

# 5. OmegaKG (Brain Consumer)
cd OmegaKG
poetry run python -m omega_kg.consumer

# 6. memOS (Hands)
cd memOS
poetry run python -m memos_mcp

# 7. InGest (Stomach) - Optional if using poller
cd InGest
poetry run python ingest/raw_lake_poller_v2.py
# OR for Dagster UI:
poetry run dagster dev -h 0.0.0.0 -p 3000

# 8. Cortex (Dashboard)
cd Cortex
npm run dev
```

### Using start_ecosystem.ps1

```powershell
# Robust startup with health checks
.\start_ecosystem.ps1 -ShowConsole

# With all options
.\start_ecosystem.ps1 -ShowConsole -Persistent -SkipMigrations
```

### Verification

```powershell
# Run E2E trace
.\scripts\operations\trace-meal.ps1

# Check all ports
@(8000,8765,8768,3000,6000,7474,7687,6380) | ForEach-Object {
    $result = Test-NetConnection -ComputerName localhost -Port $_ -WarningAction SilentlyContinue
    if ($result.TcpTestSucceeded) { Write-Host "Port $_ OPEN" } 
    else { Write-Host "Port $_ CLOSED" }
}
```

---

## Appendix A: Environment Files

### InGress/.env
```env
SOMA_INGRESS_KEY=soma-dev-secure-key-change-in-production
SOMA_PG_DSN=postgresql://omega_user:omega_dev_password@localhost:6000/soma_sensory_lake
SOMA_INGRESS_PORT=8000
```

### OmegaKG/.env
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=6000
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_PASSWORD=<secret>
REDIS_URL=redis://127.0.0.1:6380/0
SOMA_INTERNAL_KEY=<secret>
```

### memOS/.env
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=6000
MEMOS_REDIS_HOST=localhost
MEMOS_REDIS_PORT=6380
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_PASSWORD=<secret>
FASTMCP_SERVER_PORT=8768
OMEGAKG_API_URL=http://localhost:8765
```

### InGest/.env
```env
POSTGRES_DSN=postgresql://omega_user:omega_dev_password@127.0.0.1:6000/omega_kg_stable
SOMA_INTERNAL_KEY=<secret>
OMEGAKG_API_URL=http://localhost:8765
INGEST_MEMOS_BASE_URL=http://localhost:8768
```

### Cortex/.env
```env
VITE_API_OMEGA_URL=http://127.0.0.1:8765
VITE_API_INGEST_URL=http://127.0.0.1:8766
VITE_API_MEMOS_URL=http://127.0.0.1:8768
```

---

## Appendix B: Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| SSL certificate errors | PostgreSQL 17 installer sets CURL_CA_BUNDLE | Clear env vars: `$env:CURL_CA_BUNDLE=''` |
| Service won't start | Missing .env file | Check .env exists and has required vars |
| Neo4j connection refused | Container not ready | Wait 30s after `docker start` |
| memOS hangs on startup | Wrong transport mode | Ensure `--sse` flag or use fixed `__main__.py` |
| InGress 503 error | PostgreSQL not connected | Check Postgres is running on 6000 |

### Log Locations

| Service | Log Path |
|---------|----------|
| InGress | stdout / `logs/ingress.log` |
| OmegaKG | stdout / `logs/omegakg.log` |
| memOS | `d:/projects/OmegaKG/logs/memos_mcp.log` |
| InGest | `InGest/dagster_home/logs/` |
| Cortex | Browser console |

---

*Document generated: 2026-01-31*  
*Next review: After UI-Backend integration sprint*
