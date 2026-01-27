
# Guardian/Workhorse Architecture Pattern

**Document Type:** Architectural Design Record (ADR)  
**Status:** Active  
**Created:** 2026-01-15  
**Last Updated:** 2026-01-15T01:25:00+02:00  
**Significance:** 0.98 (Critical architectural constraint)

---

## Context

The OmegaKG ecosystem manages an **immutable knowledge graph** stored in Neo4j and a **vector embedding store** in PostgreSQL. Prior to this refactor, multiple services (`InGest-LLM`, `memOS.MCP`) had direct write access to these stores, creating potential for:

- Data integrity violations
- Schema inconsistencies
- Duplicate or conflicting entries
- Audit trail gaps
- Difficult debugging when data corruption occurs

---

## Decision

We implement a **Guardian/Workhorse separation pattern**:

### **OmegaKG = The Guardian**
- **SOLE authority** to write to:
  - Neo4j Knowledge Graph
  - PGVector Embeddings Store
- Validates all incoming knowledge digests
- Enforces schema constraints
- Maintains audit trails
- Acts as the "gatekeeper" for immutable knowledge

### **InGest-LLM = The Workhorse**
- Manages the **Data Lake** (`raw_ingestion` table in PostgreSQL)
- Orchestrates worker queues for processing raw data
- Creates **Knowledge Digests** from raw unstructured data
- **CANNOT write to Neo4j or Vector Store**
- Submits validated digests to OmegaKG for final persistence

### **memOS.MCP = The Memory Broker**
- Manages ephemeral working memory (Redis)
- Promotes significant memories to InGest-LLM
- **CANNOT write directly to Neo4j**
- Routes all durable persistence through the Guardian

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GUARDIAN/WORKHORSE PATTERN                       │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Raw Data Sources│
│  • Browser Ext   │
│  • GitHub Events │
│  • Linear Hooks  │
│  • Agent Memories│
└────────┬─────────┘
         │
         ▼
 ┌───────────────────────────┐
 │  InGest-LLM (Workhorse)   │◄──── PORT: 8766
 │  ┌─────────────────────┐  │
 │  │ Data Lake (PG)      │  │      RESPONSIBILITIES:
 │  │ raw_ingestion table │  │      • Store ALL raw data first
 │  └─────────────────────┘  │      • Worker queue management
 │  ┌─────────────────────┐  │      • NLP processing (chunking, entities)
 │  │ Workers/Processors  │  │      • Create Knowledge Digests
 │  │ • Conversations     │  │      
 │  │ • Terminal Logs     │  │      CONSTRAINTS:
 │  │ • Documents         │  │      ❌ NO writes to Neo4j
 │  └─────────────────────┘  │      ❌ NO writes to PGVector
 └────────┬──────────────────┘      ✅ ONLY reads from graph for context
          │
          │ Knowledge Digest
          │ (validated, structured)
          ▼
 ┌───────────────────────────┐
 │  OmegaKG (Guardian)       │◄──── PORT: 8765
 │  ┌─────────────────────┐  │
 │  │ Validation Layer    │  │      RESPONSIBILITIES:
 │  │ • Schema checks     │  │      • Validate structure & completeness
 │  │ • Dedup detection   │  │      • Check for duplicates
 │  │ • Entity resolution │  │      • Merge with existing entities
 │  └─────────────────────┘  │      • Generate embeddings (if needed)
 │  ┌─────────────────────┐  │      • Write to graph & vector store
 │  │ Persistence Layer   │  │      
 │  │ • Neo4j Writer      │  │      GUARANTEES:
 │  │ • Vector Writer     │  │      ✅ ONLY entity with graph write access
 │  │ • Audit Logger      │  │      ✅ All writes logged
 │  └─────────────────────┘  │      ✅ ACID transaction guarantees
 └────────┬──────────────────┘      ✅ Schema enforcement
          │
          ▼
 ┌───────────────────────────┐
 │  Immutable Knowledge      │
 │  ┌─────────────────────┐  │
 │  │ Neo4j Graph         │  │      READ ACCESS:
 │  │ (Nodes & Relations) │  │      • All services can read
 │  └─────────────────────┘  │      • Used for context retrieval
 │  ┌─────────────────────┐  │      • Powers semantic search
 │  │ PGVector Store      │  │      
 │  │ (Embeddings)        │  │      WRITE ACCESS:
 │  └─────────────────────┘  │      • ONLY OmegaKG Guardian
 └───────────────────────────┘
```

---

## Example: Memory Promotion Flow

```
1. Agent discovers significant insight during coding
   └─► Calls memOS.MCP.mark_significant()
        │
        ├─► memOS stores in Redis (ephemeral)
        └─► If significance >= threshold → auto-promote
             │
2. memOS.MCP.promote_memory() triggered
   └─► HTTP POST to InGest-LLM
        Endpoint: POST http://localhost:8766/ingest/experience
        Payload: {
          "source": "memos-mcp",
          "type": "working_experience",
          "content": "Docker password corruption issue...",
          "metadata": {
            "significance": 0.95,
            "session_id": "...",
            "scratchpad_context": [...]
          }
        }
             │
3. InGest-LLM (Workhorse) processes
   ├─► Stores raw JSON in raw_ingestion table (DATA LAKE)
   ├─► Worker picks up the record
   ├─► Extracts entities, concepts, relationships
   ├─► Generates Knowledge Digest:
   │    {
   │      "type": "constraint",
   │      "title": "Docker Password Special Character Trap",
   │      "entities": ["Neo4j", "Docker", "Shell"],
   │      "relationships": [
   │        {"from": "Docker", "to": "ShellExpansion", "type": "CAUSES"},
   │        {"from": "ShellExpansion", "to": "AuthFailure", "type": "LEADS_TO"}
   │      ],
   │      "embedding_required": true
   │    }
   └─► Sends digest to OmegaKG for validation
             │
4. OmegaKG (Guardian) validates and persists
   ├─► Validates schema (Constraint pattern)
   ├─► Checks for duplicates in Neo4j
   ├─► Generates embedding via Ollama
   ├─► Writes to Neo4j:
   │    CREATE (c:Constraint {
   │      id: "801528e5-...",
   │      title: "Docker Password Special Character Trap",
   │      severity: "CRITICAL",
   │      ...
   │    })
   ├─► Writes embedding to PGVector
   └─► Logs transaction to audit trail
             │
5. Memory now in Immutable Codex
   └─► Can be retrieved via:
        • memOS.MCP.retrieve_context()
        • memOS.MCP.get_constraints()
        • memOS.MCP.consult_mirmir()
```

---

## Service Ports

| Service | Port | Role | Write Permissions |
|---------|------|------|-------------------|
| memOS.MCP | 8768 | Memory Broker | Redis only |
| OmegaKG | 8765 | Guardian | Neo4j + PGVector |
| InGest-LLM | 8766 | Workhorse | PostgreSQL raw_ingestion only |
| Neo4j | 7687 | Graph Database | OmegaKG only |
| PostgreSQL | 6000 | Data Lake + Vector Store | InGest (data lake), OmegaKG (vector) |
| Redis | 6379 | Ephemeral Memory | memOS.MCP only |

---

## Architectural Constraints

### Constraint 1: Single Source of Truth for Graph Writes
```yaml
Rule: ONLY OmegaKG may write to Neo4j or PGVector
Enforcement:
  - Database user permissions locked to OmegaKG service account
  - InGest-LLM uses read-only Neo4j credentials
  - mem OS.MCP has NO Neo4j credentials
Violation Detection:
  - Audit Neo4j write logs for non-Guardian sources
  - Monitor connection strings in all service configs
Remediation:
  - Revoke write permissions from violating service
  - Route writes through OmegaKG API
```

### Constraint 2: Data Lake First Principle
```yaml
Rule: ALL raw data MUST be persisted to raw_ingestion BEFORE processing
Enforcement:
  - InGest-LLM persists to data lake before any transformation
  - Transaction rollback if data lake write fails
  - 100% data retention even if processing fails
Violation Detection:
  - Neo4j records without corresponding raw_ingestion entry
  - Compare ingestion timestamps
Remediation:
  - Backfill missing raw_ingestion records
  - Audit processing pipeline for gaps
```

### Constraint 3: Knowledge Digest Contract
```yaml
Rule: All submissions to OmegaKG MUST be structured Knowledge Digests
Format:
  - Must include: type, entities, relationships
  - Must be pre-validated by Workhorse
  - Must include provenance metadata
Enforcement:
  - OmegaKG rejects raw/unstructured submissions
  - Schema validation at Guardian ingress
Violation Detection:
  - Monitor OmegaKG rejection rate
  - Log malformed digest attempts
Remediation:
  - Fix digest generation in InGest-LLM
  - Update validation rules if specifications evolve
```

---

## Benefits

### Data Integrity
- **Single point** of graph/vector writes eliminates race conditions
- **Validation layer** prevents schema violations
- **Deduplication** enforced at one chokepoint

### Auditability
- **Every write** logged by the Guardian
- **Clear provenance** from raw data → digest → graph node
- **Rollback capability** if Guardian transaction fails

### Separation of Concerns
- **InGest-LLM** focuses on NLP and transformation logic
- **OmegaKG** focuses on knowledge integrity and consistency
- **memOS.MCP** focuses on working memory and agent experience

### Scalability
- **Horizontal scaling** of Workhorse processors (independent workers)
- **Guardian** can rate-limit writes to protect graph performance
- **Data Lake** provides buffering for burst loads

---

## Migration Notes

### For Former InGest-LLM Direct Writes:
All code paths that previously wrote to Neo4j have been refactored to:
1. Create a Knowledge Digest
2. Submit to OmegaKG via `POST /knowledge/ingest` (or equivalent)
3. Await validation response

### For Former memOS.MCP Direct Writes:
The `promote_memory()` function now:
1. POSTs to InGest-LLM `/ingest/experience`
2. InGest-LLM processes and creates digest
3. InGest-LLM submits to OmegaKG
4. OmegaKG persists to graph

**NOTE:** Port configuration is critical:
- memOS.MCP → InGest-LLM: Port **8766** (NOT 8769)
- InGest-LLM → OmegaKG: Port **8765**

---

## Verification Checklist

- [ ] No service except OmegaKG has Neo4j write credentials
- [ ] InGest-LLM has read-only Neo4j user (for context queries)
- [ ] memOS.MCP has NO Neo4j credentials at all
- [ ] All raw data hits `raw_ingestion` table first
- [ ] OmegaKG logs every graph write transaction
- [ ] Integration test: memOS → InGest → OmegaKG → Neo4j succeeds
- [ ] Port configuration matches: memOS (8768), OmegaKG (8765), InGest (8766)

---

## Related Documents

- `guardian-workhorse-architecture-status.md` - Current implementation status
- `ARCHITECTURE.md` - Overall ecosystem architecture
- `AGENTS.md` - Agent operational guidelines
- `Mirmir Protocol` - Architectural governance system

---

## Metadata

```yaml
classification: architectural_pattern
impacts:
  - data_integrity
  - service_boundaries
  - database_permissions
  - audit_compliance
stakeholders:
  - OmegaKG team
  - InGest-LLM maintainers
  - memOS.MCP developers
review_cycle: quarterly
next_review: 2026-04-15
```
