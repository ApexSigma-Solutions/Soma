# Soma Ecosystem Technical Architecture & Operations Manual

## Executive Summary

The Soma ecosystem is a **biomorphic distributed system** organized around an **organism metaphor**: Senses (InGress), Stomach (InGest), Nervous System (Redis Streams), Brain (OmegaKG/Neo4j), and Hands (memOS MCP). This architecture enables end-to-end knowledge capture, processing, and retrieval with hybrid vector search in Neo4j.

---

## Table of Contents

1. [Repository Structure](#1-repository-structure)
2. [Service Architecture Overview](#2-service-architecture-overview)
3. [API Endpoints & Contracts](#3-api-endpoints--contracts)
4. [Port Registry](#4-port-registry)
5. [Database Connections](#5-database-connections)
6. [Inter-Service Communication](#6-inter-service-communication)
7. [Design Patterns Catalog](#7-design-patterns-catalog)
8. [Critical Logic Blocks](#8-critical-logic-blocks)
9. [Non-Obvious Concepts](#9-non-obvious-concepts)
10. [Virtual Environment & Dependency Issues](#10-virtual-environment--dependency-issues)
11. [Usage Instructions](#11-usage-instructions)

---

## 1. Repository Structure

```
D:\projects\Soma\
├── InGress/                    # Senses Layer (Port 8000)
│   ├── soma_ingress/
│   │   ├── main.py             # FastAPI entry point (274 lines)
│   │   └── __init__.py
│   ├── alembic/versions/       # Database migrations
│   ├── pyproject.toml          # Poetry config (soma-ingress v0.1.0)
│   └── README.md
├── InGest/                     # Stomach Layer (Port 8766)
│   ├── src/ingest_llm_as/      # Main package
│   │   ├── main.py             # FastAPI entry point
│   │   ├── config.py           # Pydantic settings
│   │   ├── api/                # API routers
│   │   ├── core/               # Circuit breaker, webhooks
│   │   ├── dagster_ops/        # Pipeline definitions
│   │   ├── processors/         # Background processors
│   │   └── services/           # Business logic
│   ├── alembic/versions/
│   ├── pyproject.toml          # Poetry config (ingest-llm-as v0.1.0)
│   └── README.md
├── OmegaKG/                    # Brain Layer (Port 8765)
│   ├── omega_kg/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── consumer.py         # Redis stream consumer
│   │   ├── settings.py         # Bitwarden-integrated settings
│   │   ├── routers/            # API endpoints
│   │   ├── database/           # Neo4j adapters
│   │   └── workers/            # Background workers
│   ├── alembic/versions/
│   ├── pyproject.toml          # Poetry config (omega_kg v0.1.0)
│   └── README.md
├── memOS/                      # Hands Layer (Port 8768)
│   ├── src/memos_mcp/
│   │   ├── server.py           # FastMCP entry point
│   │   ├── logic.py            # MCP tool implementations
│   │   ├── config.py           # Settings
│   │   ├── database/           # Redis abstraction only
│   │   ├── memory/             # Redis storage
│   │   └── tools/              # MCP tools
│   ├── pyproject.toml          # Poetry config (memos-mcp v0.1.0)
│   └── README.md
├── Cortex/                     # Dashboard (Port 5173)
│   ├── src/
│   │   ├── App.tsx             # React entry with hash routing
│   │   ├── components/         # Feature components
│   │   ├── lib/store/          # Zustand stores
│   │   └── lib/api/            # API clients
│   ├── package.json            # npm dependencies
│   └── README.md
├── contracts/                  # API Contract Specifications
│   ├── ingress_contract.json
│   ├── ingest_contract.json
│   ├── omegakg_contract.json
│   └── memos_contract.json
├── docker-compose.yml          # Infrastructure services
├── orchestrator.py             # Legacy service spawner
├── start_ecosystem.ps1         # Master launcher script
└── scripts/
    ├── operations/             # trace-meal.ps1
    ├── database/               # Migration utilities
    └── infrastructure/         # Health checks
```

---

## 2. Service Architecture Overview

### 2.1 The Meal Trace (E2E Flow)

```
External Signal
       ↓
┌─────────────────────────────────────────────────────────────┐
│ SENSES (InGress) - Port 8000                               │
│ • HTTP endpoints for data capture                          │
│ • GitHub/Linear webhooks (ALL webhooks here)               │
│ • Writes to PostgreSQL raw_lake table                      │
└─────────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────────┐
│ STOMACH (InGest) - Port 8766                               │
│ • Polls raw_lake via Dagster                               │
│ • SimpleMem Stage 1: Entropy Gate → Coreference → Facts    │
│ • Publishes to Redis Stream (soma_working_memory)          │
└─────────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────────┐
│ NERVOUS SYSTEM (Redis) - Port 6380                         │
│ • Redis Streams for async message passing                  │
│ • Consumer group: omegakg_consumers                        │
└─────────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────────┐
│ BRAIN (OmegaKG) - Port 8765                                │
│ • Consumes from Redis Stream                               │
│ • Generates embeddings via Docker Model Runner               │
│   (Qwen 3 embedding 0.6B-F16)                          │
│ • MERGEs AtomicFact nodes into Neo4j with vectors         │
│ • Hybrid search (semantic + lexical)                       │
└─────────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────────┐
│ HANDS (memOS) - Port 8768                                  │
│ • MCP server with tools for context retrieval              │
│ • Queries OmegaKG API (NOT direct Neo4j)                  │
│ • Working memory in Redis only                           │
│ • All atomic memories stored in Neo4j                     │
└─────────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────────┐
│ DASHBOARD (Cortex) - Port 5173                             │
│ • React + TypeScript + Vite                                │
│ • Real-time SSE telemetry from all services                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Infrastructure Services (Docker)

| Service | Container Name | Internal Port | External Port | Image |
|---------|---------------|---------------|---------------|-------|
| PostgreSQL | apexsigma.postgres.soma | 5432 | 6000 | pgvector/pgvector:pg16 |
| Neo4j | apexsigma.neo4j.soma | 7687 (bolt), 7474 (http) | 7687, 7474 | neo4j:5-community |
| Redis | apexsigma.redis.soma | 6379 | 6380 | redis:7-alpine |
| Model Runner | soma-model-runner | 11434 | 11434 | Custom (Qwen 3 embedding 0.6B-F16) |

### 2.3 Memory Architecture (Neo4j-Centric)

**Previous (Deprecated):**
- ❌ Tier 1: Redis
- ❌ Tier 2: PostgreSQL + PGVector
- ❌ Tier 3: LanceDB

**Current (Neo4j-Centric):**
- ✅ Working Memory: Redis (ephemeral context)
- ✅ Atomic Memories: Neo4j with embedded vectors (768-dim)
- ✅ Hybrid Search: Neo4j vector similarity + metadata filtering

**Dynamic Node Structure:**
```
All atomic memories stored in Neo4j with:
- Dynamic variable nodes for detailed specific mapping
- Vector embeddings (768-dim from Qwen 3) for semantic search
- Metadata for hybrid filtering
- Relationships for knowledge graph
```
All atomic memories stored in Neo4j with:
- Dynamic variable nodes for detailed specific mapping
- Vector embeddings (768-dim from Qwen 3)
- Metadata for hybrid filtering
- Relationships for knowledge graph
```

---

## 3. API Endpoints & Contracts

### 3.1 InGress (Senses) - Port 8000

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/api/v1/manual/ingest` | POST | X-API-Key | Manual data ingestion |
| `/api/v1/system/vitals` | GET | X-API-Key | System telemetry (CPU/RAM/Disk) |
| `/api/v1/webhook/github` | POST | None | GitHub webhook receiver |
| `/api/v1/webhook/linear` | POST | None | Linear webhook receiver |
| `/api/v1/chrome/capture` | POST | X-API-Key | Chrome extension web captures |
| `/api/v1/terminal/ghost` | POST | X-API-Key | Terminal command logs (Ghost) |
| `/api/v1/telemetry/stream` | GET | None | SSE telemetry stream |

**Key Details:**
- Default API Key: `sigma-dev-secret-key` (line 23, main.py)
- Database: `soma_sensory_lake` on PostgreSQL port 6000
- **ALL webhooks are in InGress** (GitHub, Linear, etc.)

### 3.2 InGest (Stomach) - Port 8766

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check with circuit breaker status |
| `/metrics` | GET | None | Prometheus metrics |
| `/ingest/text` | POST | None | Text ingestion with chunking |
| `/ingest/file` | POST | None | File upload (PDF, text, markdown) |
| `/omega/query_context` | POST | None | Query Master Knowledge Graph |
| `/ingest/experience` | POST | None | Ingest working experience from memOS |
| `/ingest/digest` | POST | None | Synthesize conversation into structured digest |
| `/ingest/queue` | GET | None | Get conversation queue status |
| `/ingest/stats` | GET | None | Get comprehensive ingestion statistics |

**SimpleMem Pipeline:**
```python
# Entropy Gate (H > 0.35) → Coreference Resolution → Temporal Anchoring → Atomic Fact Synthesis
```

### 3.3 OmegaKG (Brain) - Port 8765

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/v1/guardian/validate` | POST | SOMA_INTERNAL_KEY | Validate against Codex |
| `/v1/guardian/commit` | POST | SOMA_INTERNAL_KEY | Commit knowledge to Neo4j |
| `/v1/guardian/store_embedding` | POST | SOMA_INTERNAL_KEY | Store vector embedding |
| `/v1/capture` | POST/OPTIONS | JWT | Conversation capture |
| `/v1/capture/terminal/` | POST | JWT | Terminal command capture |
| `/v1/recent` | GET | JWT | Get recent captures |
| `/v1/stats` | GET | JWT | Get capture statistics |
| `/v1/api/v1/telemetry/stream` | GET | None | SSE telemetry stream |
| `/v1/validate/health` | GET | None | Validation API health |
| `/v1/validate/validate-and-store` | POST | None | Validate and store knowledge |
| `/v1/mcp/tools/consult_codex` | POST | None | Consult Codex before actions |

**Removed Endpoints (Moved to InGress):**
- ❌ `/v1/webhooks/linear` - NOW in InGress
- ❌ `/v1/webhooks/github` - NOW in InGress

**Bitwarden Secret Mappings:**
```python
"linear_webhook_secret": "LINEAR_WEBHOOK_SECRET_PRD_ID"
"postgres_password": "POSTGRES_PASSWORD_PRD_ID"
"neo4j_password": "NEO4J_PASSWORD_PRD_ID"
"jwt_secret_key": "JWT_SECRET_KEY_ID"
```

### 3.4 memOS (Hands) - Port 8768

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with service status |
| `/sse` | GET | MCP Server-Sent Events |
| `/stats` | GET | Memory statistics |
| `/pulse/emit` | POST | Emit pulse event |
| `/pulse/stream` | GET | SSE pulse stream |
| `/memory/{tier}/store` | POST | Store memory (InGest-LLM bridge) |
| `/mirmir/consult` | POST | Mirmir consultation (Dashboard) |

**MCP Tools Exposed:**
```python
# Intelligence Layer
consult_mirmir()          # Validates actions against Codex
verify_implementation()   # Reviews code changes

# Context Retrieval (via OmegaKG API)
retrieve_context()        # Query OmegaKG, NOT direct Neo4j
get_concepts()           # Query OmegaKG for graph concepts
get_constraints()        # Query OmegaKG for Mirmir constraints

# Working Memory (Redis)
scratch_write()          # Write to scratchpad
scratch_read()           # Read scratchpad
set_working_memory()     # Set context
get_working_memory()     # Retrieve session working memory

# Memory Promotion
mark_significant()       # Mark for promotion
promote_memory()         # Promote to InGest

# Soma Ecosystem Integration
ingest_signal()          # Push data to InGress (Senses)
query_brain()           # Query OmegaKG API (read-only access)
promote_to_codex()      # Promote constraints to OmegaKG Codex
```

**Critical Architectural Change:**
- memOS **NEVER queries Neo4j directly**
- All graph queries go through **OmegaKG API**
- OmegaKG is the **sole Neo4j writer**
- This maintains single source of truth for the Brain

---

## 4. Port Registry

### Service Ports

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| InGress | 8000 | HTTP | Data capture API, webhooks |
| OmegaKG | 8765 | HTTP | Brain API, Guardian |
| InGest | 8766 | HTTP | Processing API |
| memOS | 8768 | HTTP/SSE | MCP server |
| Cortex | 5173 | HTTP | Dashboard (Vite dev) |

### Infrastructure Ports

| Service | External | Internal | Purpose |
|---------|----------|----------|---------|
| PostgreSQL | 6000 | 5432 | Primary database (new soma container) |
| Neo4j (Bolt) | 7687 | 7687 | Graph database protocol (new soma container) |
| Neo4j (HTTP) | 7474 | 7474 | Browser UI (new soma container) |
| Redis | 6380 | 6379 | Message broker |
| Model Runner | 11434 | 11434 | Embedding model server (Qwen 3 embedding 0.6B-F16) |

### Network Configuration

```yaml
# Docker network: apexsigma.net
# Subnet: 172.20.0.0/16
# Tailscale gateway: 172.20.0.254

# NEW Container Naming (Replaced deprecated containers)
apexsigma.postgres.soma       # Replaces apexsigma.postgres.stable (DEPRECATED)
apexsigma.neo4j.soma          # Replaces apexsigma.neo4j.stable (DEPRECATED)
apexsigma.redis.soma           # Unchanged
```

---

## 5. Database Connections

### 5.1 PostgreSQL (apexsigma.postgres.soma)

**Connection String Pattern:**
```python
# From host (Windows)
postgresql://omega_user:omega_dev_password@localhost:6000/database_name

# From Docker containers
postgresql://omega_user:omega_dev_password@apexsigma.postgres.soma:5432/database_name
```

**Databases:**
| Database | Purpose | Services |
|----------|---------|----------|
| soma_sensory_lake | Raw data capture | InGress, InGest |
| omega_kg_soma | OmegaKG metadata (vectors table) | OmegaKG |

**Decommissioned Containers:**
- ❌ `apexsigma.postgres.stable` - REPLACED BY `apexsigma.postgres.soma`

**Key Tables:**
```sql
-- InGress raw_lake
CREATE TABLE raw_lake (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(64) NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    client_ip VARCHAR(45),
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    failed BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);

-- OmegaKG vectors (for external indexing if needed)
CREATE TABLE omega_vectors_768 (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT,
    node_label VARCHAR(64),
    embedding VECTOR(768),
    status VARCHAR(32),
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5.2 Neo4j (apexsigma.neo4j.soma)

**Connection Pattern:**
```python
# From host
bolt://localhost:7687

# From containers
bolt://apexsigma.neo4j.soma:7687
```

**Decommissioned Containers:**
- ❌ `apexsigma.neo4j.stable` - REPLACED BY `apexsigma.neo4j.soma`

**Node Labels (Dynamic Variable Nodes):**
- `AtomicFact` - Core knowledge units with embeddings (768-dim vectors from Qwen 3)
- `MemoryAtom` - Digest containers
- `Task` - Task management
- `LinearIssue` - Linear integration
- `Constraint` - Codex governance rules
- `Context` - Governance scopes
- `Entity` - Named entities (persons, locations, etc.)
- `Concept` - Semantic concepts
- `CodeBlock` - Source code blocks
- `ErrorLog` - Error entries
- **Dynamic nodes** - For detailed specific mapping based on content type

**Vector Storage in Neo4j:**
```cypher
-- AtomicFact with embedded vector property
MERGE (f:AtomicFact {text_hash: $text_hash})
SET
    f.text = $text,
    f.embedding = $embedding,  -- 768-dim float array from Qwen 3
    f.source_id = $source_id,
    f.source = $source,
    f.metadata = $metadata,
    f.created_at = datetime()
```

**Key Cypher Operations:**
```cypher
-- Hybrid search (semantic + lexical)
CALL db.index.vector.queryNodes(
    'atomic_fact_vector_index',  -- Vector index name
    $query_embedding,            -- Qwen 3 embedding (768-dim)
    {
        topK: 10,
        scoreThreshold: 0.75
    }
) YIELD node, score
WHERE node:AtomicFact
RETURN node, score
ORDER BY score DESC
LIMIT 10
```

### 5.3 Redis (apexsigma.redis)

**Connection Pattern:**
```python
# From host
redis://localhost:6380/0

# From containers
redis://apexsigma.redis.soma:6379/0
```

**Key Streams:**
- `soma_working_memory` - Main message bus (InGest → OmegaKG)
- `pulse:stream` - Event consolidation stream

**Consumer Groups:**
- `omegakg_consumers` - OmegaKG brain consumers

**Working Memory Structure:**
```python
# Session-based working memory (ephemeral)
memos:{session_id}:working    # Hash for current context
memos:{session_id}:scratch     # List for reasoning trace
memos:{session_id}:pending     # List for promotion queue

# TTL Configuration
- Working Memory: 1 hour
- Scratchpad: 2 hours
- Pending Memories: 4 hours
```

---

## 6. Inter-Service Communication

### 6.1 Communication Patterns

```
┌──────────┐     HTTP      ┌──────────┐
│ InGress  │──────────────→│ InGest   │
│ (8000)   │   (Raw Lake)  │ (8766)   │
└──────────┘               └────┬─────┘
                                │
                                │ Redis Stream
                                ↓
┌──────────┐     HTTP      ┌──────────┐
│ memOS    │←──────────────│ OmegaKG  │
│ (8768)   │   (Guardian)  │ (8765)   │
└──────────┘               └────┬─────┘
                                │
                                │ Neo4j (Bolt)
                                ↓
                        ┌──────────┐
                        │  Neo4j   │
                        │ (7687)   │
                        └──────────┘
```

### 6.2 Message Formats

**Redis Stream Message (InGest → OmegaKG):**
```json
{
  "source_id": "uuid",
  "fact_units": ["atomic fact 1", "atomic fact 2"],
  "metadata": {
    "source": "terminal_ghost",
    "event_type": "shell_capture",
    "entropy": 0.85,
    "timestamp": "2026-01-28T12:00:00Z",
    "embedding": [768-dim float array]  // Generated by Qwen 3
  }
}
```

**Knowledge Digest (InGest → OmegaKG Guardian):**
```python
class KnowledgeDigest(BaseModel):
    source_id: str
    title: str
    summary: str
    type: str
    facts: list[str]
    entities: list[str]
    embedding: list[float]  # 768-dim from Qwen 3
    metadata: dict
```

### 6.3 Internal API Keys

| Service | Key Name | Default Value | Location |
|---------|----------|---------------|----------|
| InGress | SOMA_INGRESS_KEY | `sigma-dev-secret-key` | main.py:23 |
| OmegaKG | SOMA_INTERNAL_KEY | `soma_dev_key` | settings.py |
| OmegaKG | JWT_SECRET_KEY | `legacy_fallback_secret` | settings.py:193 |

---

## 7. Design Patterns Catalog

### 7.1 Singleton Pattern (8 implementations)

**Double-Checked Locking (Thread-safe):**
```python
# memOS database/__init__.py:21-42
_db_instance = None
_db_lock = threading.Lock()

def get_database():
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = _create_database()
    return _db_instance
```

**Classic __new__ Singleton:**
```python
# OmegaKG database/graph.py:18-30
class AsyncGraphDriver:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### 7.2 Factory Pattern

**Abstract Database Factory:**
```python
# memOS database/__init__.py:25-42
def get_database():
    # Simplified - only Redis working memory now
    db_type = settings.memos_db_type
    if db_type == "redis":
        return RedisMemoryClient()
    # PostgreSQL and Neo4j accessed via API now
```

### 7.3 Circuit Breaker Pattern

**Full Implementation (InGest):**
```python
# InGest core/circuit_breaker.py:26-263
class CircuitBreaker:
    states = ["CLOSED", "OPEN", "HALF_OPEN"]
    
    def record_failure(self):
        # Increment counter, transition to OPEN on threshold
        
    def record_success(self):
        # Reset counter, transition HALF_OPEN → CLOSED
        
    def is_closed(self):
        # Auto-transition OPEN → HALF_OPEN after timeout
```

### 7.4 Repository Pattern

**Database Abstraction:**
```python
# memOS database/base.py (Abstract Base)
class Database(ABC):
    @abstractmethod
    def store_memory(self, content, agent_id, metadata): ...
    
    @abstractmethod
    def search_memories(self, query, top_k): ...

# Simplified: Only Redis working memory
# Graph access via OmegaKG API
```

### 7.5 Consumer Pattern

**Redis Stream Consumer:**
```python
# OmegaKG consumer.py:63-303
class BrainConsumer:
    async def start(self):
        while self._running:
            messages = await self._redis.xreadgroup(...)
            for message in messages:
                await self._process_digest(message)
                await self._redis.xack(stream, group, message_id)
```

### 7.6 Event-Driven Pattern

**Pulse Emitter (Event Publishing):**
```python
# InGest shared/pulse_emitter.py:20-195
class PulseEmitter:
    async def emit(self, event_type, payload):
        await self._redis.xadd("pulse:stream", {
            "type": event_type,
            "payload": json.dumps(payload),
            "timestamp": datetime.utcnow().isoformat()
        })
```

---

## 8. Critical Logic Blocks

### 8.1 SimpleMem Stage 1 (Metabolism)

**Location:** InGest processors/

**Pipeline:**
```python
1. Entropy Gate (H > 0.35)
   ↓
2. Coreference Resolution (coreferee/spaCy)
   ↓
3. Temporal Anchoring (dateparser)
   ↓
4. Atomic Fact Synthesis
   ↓
5. Embedding Generation (Qwen 3 embedding 0.6B-F16 via Docker Model Runner)
   ↓
6. Publish to Redis Stream
```

**Key Files:**
- `processors/conversation_ingestor.py` - Polls raw_ingestions
- `utils/content_processor.py` - Chunking
- `services/llm_summarizer.py` - LLM integration

### 8.2 Guardian Pattern (Immune System)

**Location:** OmegaKG routers/guardian.py

**Purpose:** Sole Neo4j writer, validates before persistence

**Key Method:**
```python
# guardian.py:213-278
@router.post("/commit")
async def commit_knowledge(request: KnowledgeCommitRequest):
    # 1. Codex validation
    # 2. Relevance scoring
    # 3. Graph storage (Neo4j with vectors)
    # 4. Vault storage (Obsidian)
    # 5. Redis acknowledgment
```

### 8.3 Bitwarden Secrets Integration

**Location:** OmegaKG settings.py:59-154

**Pattern:**
```python
class BitwardenSettingsSource(PydanticBaseSettingsSource):
    """Fetches secrets from Bitwarden Secrets Manager."""
    
    secret_mapping = {
        "linear_webhook_secret": "LINEAR_WEBHOOK_SECRET_PRD_ID",
        "postgres_password": "POSTGRES_PASSWORD_PRD_ID",
        "neo4j_password": "NEO4J_PASSWORD_PRD_ID",
        # ... 10+ mappings
    }
```

### 8.4 Async Context Managers (Mandatory Pattern)

**Neo4j Sessions:**
```python
# CORRECT - Always use async context managers
async with driver.session() as session:
    result = await session.run("MATCH (n) RETURN n")
    record = await result.single()
# Session auto-closed
```

**PostgreSQL (asyncpg):**
```python
# CORRECT
async with pool.acquire() as conn:
    row = await conn.fetchrow("SELECT * FROM table WHERE id = $1", id)
```

### 8.5 Cypher Query Construction

**SAFE (Parameterized):**
```cypher
// consumer.py:273-300
MERGE (f:AtomicFact {text_hash: $text_hash})
SET f.text = $text, f.embedding = $embedding
```

**UNSAFE (String Interpolation - CRITICAL):**
```cypher
// guardian.py:293-302
MERGE (n:{request.node_label} {raw_id: $raw_id})  // INJECTION RISK
```

### 8.6 Dynamic Node Architecture

**Pattern:**
```python
# OmegaKG dynamically creates nodes based on content type
node_labels = {
    "code": "CodeBlock",
    "error": "ErrorLog",
    "task": "Task",
    "entity": "Entity",
    # ... dynamic mapping
}

# Each node type has specific properties
if content_type == "code":
    create_node("CodeBlock", {code, language, hash, embedding})
elif content_type == "error":
    create_node("ErrorLog", {error, traceback, embedding})
```

---

## 9. Non-Obvious Concepts

### 9.1 Neo4j-Centric Architecture

**Previous (Deprecated):**
```
Redis → PostgreSQL → LanceDB (Tiered memory)
```

**Current:**
```
Redis (working) → OmegaKG API → Neo4j (atomic memories + vectors)
```

**Key Changes:**
- All vectors stored in Neo4j node properties
- No PGVector or LanceDB
- memOS queries OmegaKG API, NOT Neo4j directly
- OmegaKG is sole Neo4j writer

### 9.2 Embedding Model Migration

**Previous (Deprecated):**
- ❌ BGE-M3 via Ollama
- ❌ Multiple embedding services

**Current:**
- ✅ Qwen 3 embedding 0.6B-F16
- ✅ Served by Docker Model Runner
- ✅ Single consistent embedding source
- ✅ 768-dimensional vectors

### 9.3 Webhook Migration

**Previous:**
- GitHub/Linear webhooks in OmegaKG

**Current:**
- **ALL webhooks in InGress** (Senses layer)
- OmegaKG focuses on brain persistence

### 9.4 Container Naming

**Deprecated (DO NOT USE):**
- ❌ `apexsigma.postgres.stable`
- ❌ `apexsigma.neo4j.stable`

**Current:**
- ✅ `apexsigma.postgres.soma`
- ✅ `apexsigma.neo4j.soma`

### 9.5 Settings Non-Caching Pattern

**InGest Convention:**
```python
// DON'T (ContentProcessor violates this at line 14)
from config import settings  // Module-level cached

// DO
from config import get_settings  // Function returns fresh instance
settings = get_settings()  // Reloads from .env on every call
```

### 9.6 Zero-Trust Enforcement

**Location:** OmegaKG settings.py:380-416

**Behavior:**
- In `stable`/`prod` environments
- Requires `BWS_ACCESS_TOKEN` (Bitwarden)
- Validates all secrets are fetched from vault
- Fails fast on missing secrets

### 9.7 Mock Mode Auto-Fallback

**Location:** OmegaKG lifecycle.py:118-120

```python
if not neo4j_connected:
    logger.warning("Switching to mock mode")
    return MockLifecycleEnforcer()  // Returns mock results
```

### 9.8 POML Serialization

**InGest Convention:** All knowledge graph data uses XML-based POML (Prompt Markup Language) for structured prompts.

**Location:** `InGest/prompts/` directory

### 9.9 Dead Letter Queue (DLQ)

**InGress raw_lake columns:**
- `failed` - Boolean flag
- `retry_count` - Attempt counter
- `last_error` - Error message

**Usage:** Records that fail processing 3+ times are flagged for manual review.

### 9.10 UTF-8 Encoding Requirement

**MANDATORY:** All file I/O must specify `encoding="utf-8"`.

```python
// CORRECT
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

// INCORRECT (platform-dependent)
with open(filepath, "w") as f:  // DON'T
    f.write(content)
```

---

## 10. Virtual Environment & Dependency Issues

### 10.1 Current State

**CRITICAL FINDING:** No virtual environments exist in any service.

```bash
// Poetry cache location
D:\projects\Soma\.poetry-cache\virtualenvs
dir /b .poetry-cache\virtualenvs
// Result: No virtualenvs found in cache
```

**Missing .venv directories:**
- ❌ `InGress/.venv` - Not found
- ❌ `InGest/.venv` - Not found
- ❌ `OmegaKG/.venv` - Not found
- ❌ `memOS/.venv` - Not found

### 10.2 Poetry Configuration

**Current Settings:**
```
virtualenvs.create = true
virtualenvs.in-project = true
virtualenvs.path = "{cache-dir}\\virtualenvs"
```

### 10.3 Lock File Status

| Service | poetry.lock | Status |
|---------|-------------|--------|
| InGress | ❌ Missing | **CRITICAL** |
| InGest | ✅ Present | OK |
| OmegaKG | ✅ Present | OK |
| memOS | ✅ Present | OK |

### 10.4 Dependency Conflicts

**Critical Issues Identified:**

1. **Pytest Version Mismatch:**
   - InGest: `pytest = "^8.2.2"`
   - OmegaKG: `pytest = "^9.0.2"`
   - Conflict: Cannot install both simultaneously

2. **Pydantic-Settings Version Spread:**
   - InGress: `>=2.10.1,<3.0.0`
   - InGest: `>=2.10.1,<3.0.0`
   - OmegaKG: `>=2.11.0,<3.0.0`
   - memOS: `^2.0.0`

3. **Neo4j Driver Version:**
   - OmegaKG: `>=6.0.0,<7.0.0`
   - memOS: `>=6.0.0,<7.0.0`
   - ✅ Compatible

4. **Asyncpg Version:**
   - InGress: `^0.29.0`
   - InGest: `^0.29.0`
   - OmegaKG: `>=0.29.0`
   - memOS: `^0.30.0`
   - Conflict: memOS requires 0.30, others 0.29

### 10.5 TLS/SSL Certificate Issues

**Python 3.12 on Windows:**

1. **Certifi Package:** May need update for latest certificates
2. **Poetry Installation:** May fail with SSL verification errors
3. **Workaround:** Use `--trusted-host` flags in pip fallback

**Remediation (in start_ecosystem.ps1):**
```powershell
// Install-PipWithTrustedHosts function (line 138-151)
function Install-PipWithTrustedHosts {
    param([string]$Package)
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org $Package
}
```

### 10.6 Docker Infrastructure Status

**Containers (as of audit):**
```
apexsigma.redis.soma      Exited (255) 22 hours ago
apexsigma.neo4j.soma      Exited (255) 22 hours ago  (NEW container name)
apexsigma.postgres.soma   Exited (255) 22 hours ago  (NEW container name)
```

**Status:** All infrastructure containers are stopped. Docker start commands timeout (120s).

---

## 11. Usage Instructions

### 11.1 Initial Setup

```powershell
// 1. Start infrastructure (requires Docker with NEW container names)
docker-compose up -d postgres neo4j redis

// Verify new containers exist
docker ps -a | findstr soma
// Expected: apexsigma.postgres.soma, apexsigma.neo4j.soma, apexsigma.redis.soma

// 2. Run database migrations
python scripts/database/migrate_all.py upgrade

// 3. Start Docker Model Runner
docker run -d --name soma-model-runner \
  -p 11434:11434 \
  -e MODEL=qwen3-embedding:0.6B-F16 \
  soma/model-runner:latest

// 4. Validate API contracts
python contracts/validate_contracts.py

// 5. Start ecosystem
.\start_ecosystem.ps1 -ShowConsole  // Debug mode
.\start_ecosystem.ps1              // Production (hidden windows)
```

### 11.2 Manual Service Startup

**If automatic startup fails, start individually:**

```powershell
// Terminal 1 - InGress
cd InGress
poetry install
poetry run python -m soma_ingress.main

// Terminal 2 - InGest
cd InGest
poetry install
poetry run python -m ingest_llm_as.main

// Terminal 3 - OmegaKG
cd OmegaKG
poetry install
poetry run python -m omega_kg.main

// Terminal 4 - memOS
cd memOS
poetry install
poetry run python -m memos_mcp.server --sse

// Terminal 5 - Cortex
cd Cortex
npm install
npm run dev
```

### 11.3 E2E Testing

```powershell
// Run meal trace verification
.\scripts\operations\trace-meal.ps1

// Manual verification in Neo4j Browser (http://localhost:7474)
MATCH (f:AtomicFact)
WHERE f.source = 'terminal_ghost'
RETURN f.text, f.source_id, f.embedding[0..5], f.created_at
ORDER BY f.created_at DESC
LIMIT 10
```

### 11.4 Health Check Endpoints

```bash
// Check all services
curl http://localhost:8000/health   // InGress
curl http://localhost:8766/health   // InGest
curl http://localhost:8765/health   // OmegaKG
curl http://localhost:8768/health   // memOS
```

### 11.5 Key Environment Variables

**InGress (.env):**
```bash
SOMA_INGRESS_KEY=sigma-dev-secret-key
SOMA_PG_DSN=postgresql://omega_user:omega_dev_password@localhost:6000/soma_sensory_lake
SOMA_INGRESS_PORT=8000
REDIS_URL=redis://localhost:6380/0
```

**OmegaKG (.env):**
```bash
NEO4J_URI=bolt://apexsigma.neo4j.soma:7687  // NEW container
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
POSTGRES_HOST=apexsigma.postgres.soma  // NEW container
POSTGRES_PORT=5432
SOMA_INTERNAL_KEY=soma_dev_key
MODEL_RUNNER_URL=http://soma-model-runner:11434  // Docker Model Runner
BWS_ACCESS_TOKEN=  // Required in stable/prod
```

**memOS (.env):**
```bash
MEMOS_DB_TYPE=redis  // Simplified - only working memory
OMEGAKG_API_URL=http://localhost:8765  // Query OmegaKG API
MEMOS_REDIS_HOST=apexsigma.redis.soma
MEMOS_REDIS_PORT=6379
```

---

## Appendix A: File Reference

### Critical Files by Service

| Service | Critical Files | Purpose |
|---------|---------------|---------|
| InGress | soma_ingress/main.py | FastAPI app, API endpoints, webhooks |
| | pyproject.toml | Dependencies |
| InGest | src/ingest_llm_as/main.py | FastAPI entry |
| | src/ingest_llm_as/config.py | Settings management |
| | src/ingest_llm_as/core/circuit_breaker.py | Circuit breaker |
| | src/ingest_llm_as/processors/ | Background workers |
| OmegaKG | omega_kg/main.py | FastAPI entry |
| | omega_kg/settings.py | Bitwarden integration |
| | omega_kg/consumer.py | Redis consumer |
| | omega_kg/routers/guardian.py | Sole Neo4j writer |
| | omega_kg/database/graph.py | Neo4j driver |
| memOS | src/memos_mcp/server.py | MCP server |
| | src/memos_mcp/logic.py | Tool implementations |
| | src/memos_mcp/memory/redis_client.py | Working memory only |
| Cortex | src/App.tsx | Main React app |
| | src/lib/store/ | Zustand stores |
| | src/lib/api/client.ts | API clients |

---

**Document Version:** 2.0  
**Last Updated:** 2026-01-28  
**Audit Scope:** Full ecosystem analysis with architectural corrections  
**Total Services:** 5 (InGress, InGest, OmegaKG, memOS, Cortex)  
**Infrastructure:** 4 (PostgreSQL soma, Neo4j soma, Redis, Model Runner)  
**Key Changes from v1.0:**
- ✅ Corrected embedding model (Qwen 3 0.6B-F16, Docker Model Runner)
- ✅ Corrected vector dimensions (768-dim from Qwen 3, not 1024)
- ✅ Removed deprecated containers (stable → soma)
- ✅ Moved webhooks from OmegaKG to InGress
- ✅ Updated architecture (Neo4j-centric, no PGVector/LanceDB)
- ✅ Corrected memOS behavior (OmegaKG API queries, not direct Neo4j)
- ✅ Added dynamic node structure documentation