# Guardian/Workhorse Architecture - Status Report
**Generated:** 2026-01-15T01:15:42+02:00

## TL;DR: Memories Not Persisted (As Expected)

The `mark_significant` memories were **accepted by memOS.MCP** but **NOT persisted to Neo4j** because:

1. ✅ **Architecture is correctly enforced** - OmegaKG is the sole Guardian
2. ⚠️ **memOS.MCP → InGest-LLM → OmegaKG pipeline not fully wired**
3. ❌ **InGest-LLM service was not running during memory submission**

---

## Current Architecture (Post-Refactor)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Flow: Guardian Pattern                   │
└─────────────────────────────────────────────────────────────────┘

 Raw Data Sources
      │
      ├─► Browser Extension (Conversations)
      ├─► GitHub Webhooks (Commits, Issues)
      ├─► Linear Webhooks (Tasks)
      └─► memOS.MCP (Agent Memories)
           │
           ▼
    ┌──────────────────────┐
    │  InGest-LLM.as       │ ◄──── WORKHORSE
    │  (The Digestor)      │       • Manages raw_ingestion table
    └──────────┬───────────┘       • Runs workers/processors
               │                   • Creates Knowledge Digests
               │                   • NO WRITES to Neo4j/Vector
               ▼
        Knowledge Digest
               │
               ▼
    ┌──────────────────────┐
    │  OmegaKG             │ ◄──── GUARDIAN
    │  (Gatekeeper)        │       • SOLE authority to write:
    └──────────┬───────────┘         - Neo4j Graph
               │                     - PGVector Embeddings
               ▼                   • Validates all ingests
    ┌──────────────────────┐       • Enforces schema
    │  Immutable Knowledge │
    │  • Neo4j Graph       │
    │  • Vector Store      │
    └──────────────────────┘
```

---

## The memOS.MCP Memory Flow (Intended vs Actual)

### Intended Flow (What Should Happen):

```
1. Agent calls mark_significant()
   └─► memOS.MCP stores in Redis (pending)
        │
2. mark_significant() auto-promotes if significance >= threshold
   └─► promote_memory() called
        │
3. promote_memory() sends HTTP POST to InGest-LLM
   └─► POST /ingest/experience
        │
4. InGest-LLM processes → Knowledge Digest
   └─► Sends to OmegaKG for validation
        │
5. OmegaKG validates and writes to Neo4j + Vector Store
   └─► Memory now in Codex
```

### Actual Flow (What Happened):

```
1. Agent calls mark_significant() ✅
   └─► memOS.MCP stores in Redis ✅
        │
2. Auto-promote triggered (significance = 0.95, 0.92) ✅
   └─► promote_memory() called ✅
        │
3. HTTP POST to InGest-LLM ❌ FAILED
   └─► "All connection attempts failed"
        │
4. Memories remain in Redis ephemeral storage
   └─► Will be lost on Redis restart
```

---

## Root Causes

### 1. InGest-LLM Service Not Running
The `promote_memory` function attempted to POST to:
```
http://localhost:8769/ingest/experience
```

But InGest-LLM service was not running during our session.

### 2. Connection Configuration
Check memOS.MCP config:
```bash
# In memos.MCP/.env or settings
INGEST_LLM_URL=http://localhost:8769
```

Verify InGest-LLM is running on this port.

### 3. Endpoint Compatibility
The `/ingest/experience` endpoint exists in InGest-LLM:
```python
# File: InGest-LLM.as/src/ingest_llm_as/api/ingestion.py:486
@router.post("/experience")
async def ingest_experience(
    request: WorkingExperienceRequest,
    background_tasks: BackgroundTasks,
    memos_client: MemOSClient = Depends(get_memos_client),
):
    """Ingest a working experience promoted from memOS.MCP."""
```

✅ **Endpoint exists and is compatible**

---

## Memory IDs Created (Currently Ephemeral)

| Memory ID | Significance | Content Preview | Status |
|-----------|-------------|-----------------|--------|
| `801528e5-e8d5-4d76-a3cf-a0d71f0b2643` | 0.95 | Docker Password Special Character Constraint | ⚠️ Redis only |
| `07ec80d0-6332-4129-8811-bbced08e689b` | 0.92 | Neo4j Password Reset Success Report | ⚠️ Redis only |

---

## Guardian Pattern Enforcement ✅

**Good News:** The architecture is correctly enforced!

- ❌ memOS.MCP does NOT write directly to Neo4j
- ❌ InGest-LLM does NOT write directly to Neo4j
- ✅ Only OmegaKG has write permissions

This is exactly as designed.

---

## Action Items to Persist Memories

### Option 1: Start InGest-LLM and Re-submit

```powershell
# 1. Start InGest-LLM service
cd InGest-LLM.as
poetry run uvicorn src.ingest_llm_as.main:app --host 0.0.0.0 --port 8769

# 2. Verify it's running
curl http://localhost:8769/health

# 3. Re-submit memories via memOS.MCP
# (The agent can call mark_significant again)
```

### Option 2: Manual Ingestion via InGest-LLM API

```bash
# POST directly to InGest-LLM
curl -X POST http://localhost:8769/ingest/experience \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "type": "constraint",
    "content": "Docker Password Special Character Constraint...",
    "metadata": {
      "significance": 0.95,
      "reason": "Critical architectural constraint"
    }
  }'
```

### Option 3: Use OmegaKG Direct Ingestion (If Available)

Check if OmegaKG has a `/knowledge/ingest` endpoint for pre-validated digests.

---

## Architectural Constraints to Document

**These should be added to the Codex:**

### Constraint 1: Immutable Knowledge Guardian Pattern

```yaml
Title: "OmegaKG is Sole Knowledge Graph Authority"
Type: Architectural Constraint
Severity: CRITICAL
Rule: |
  ONLY OmegaKG is permitted to write to:
  - Neo4j Graph Database
  - PGVector Embeddings
  
  All other services (InGest-LLM, memOS.MCP, etc.) MUST:
  - Submit Knowledge Digests to OmegaKG for validation
  - Never write directly to graph or vector store
  
Violation Detection: |
  - Check Neo4j connection strings in non-OmegaKG services
  - Scan for direct pgvector writes outside OmegaKG
  
Remediation: |
  - Remove write permissions from service database users
  - Create read-only connections for non-Guardian services
  - Route all writes through OmegaKG API
```

### Constraint 2: Data Lake First Principle

```yaml
Title: "All Raw Data Must Touch Data Lake First"
Type: Data Flow Constraint
Severity: HIGH
Rule: |
  Before any processing, ALL raw data must be persisted to:
  - PostgreSQL raw_ingestion table (via InGest-LLM)
  
  This ensures 100% data retention even if processing fails.
  
Flow: |
  Raw Data → InGest-LLM.raw_ingestion → Workers → Digest → OmegaKG
  
Violation Detection: |
  - Data appearing in Neo4j without corresponding raw_ingestion record
  
Remediation: |
  - Backfill missing raw_ingestion records
  - Update ingestion pipeline to write to data lake first
```

---

## Service Dependency Map

```
memOS.MCP (Port: 8768)
   ├─► Redis (Port: 6379) - Working Memory
   └─► InGest-LLM (Port: 8769) - For memory promotion
        │
InGest-LLM (Port: 8769)
   ├─► PostgreSQL (Port: 6000) - raw_ingestion table
   └─► OmegaKG (Port: 8765) - Knowledge validation
        │
OmegaKG (Port: 8765)
   ├─► Neo4j (Port: 7687) - Graph writes
   └─► PostgreSQL (Port: 6000) - Vector writes
```

---

## Verification Commands

```powershell
# Check if InGest-LLM is running
curl http://localhost:8769/health

# Check if OmegaKG is running
curl http://localhost:8765/health

# Check if memories are in Redis (ephemeral)
docker exec apexsigma.redis redis-cli KEYS "*801528e5*"

# Check if memories made it to Neo4j (durable)
docker exec apexsigma.neo4j.stable cypher-shell -u neo4j -p "LMKXBmMtMMRnAdeotR81FEIZ2UFnD0Ec" \
  "MATCH (m:Memory {id: '801528e5-e8d5-4d76-a3cf-a0d71f0b2643'}) RETURN m;"
```

---

## Recommendations

1. **Start InGest-LLM Permanently**
   - Add to `start_ecosystem.ps1` if not already there
   - Ensure it starts before memOS.MCP

2. **Add Health Check Monitoring**
   - memOS.MCP should check InGest-LLM health before promoting
   - Fail gracefully with retry logic

3. **Document the Pipeline**
   - Add flowcharts to ARCHITECTURE.md
   - Include service dependency tree

4. **Create Integration Tests**
   - End-to-end test: memOS.MCP → InGest → OmegaKG → Neo4j
   - Verify memory appears in graph after promotion

---

## Summary

| Component | Status | Role |
|-----------|--------|------|
| memOS.MCP | ✅ Running | Memory staging (Redis) |
| InGest-LLM | ❌ Not Running | Workhorse (Processing) |
| OmegaKG | ✅ Running | Guardian (Graph writes) |
| Neo4j | ✅ Running | Immutable knowledge store |
| Memories | ⚠️ Redis Only | Need re-submission |

**Next Step:** Start InGest-LLM service and re-submit the Neo4j password constraint memories.
