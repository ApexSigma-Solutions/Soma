# Soma E2E Meal Trace - Manual Verification Guide

## Prerequisites Installation

The orchestrator needs `structlog` in the base Python environment:

```powershell
# Install with --trusted-host to bypass certificate issues
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org structlog
```

---

## Step 1: Start the Organism

```powershell
cd d:\projects\Soma
python orchestrator.py
```

**Expected:** 4 console windows open (InGress, InGest, OmegaKG Consumer, memOS)

---

## Step 2: Verify Services are Running

### Check InGress (Senses)
```powershell
curl http://localhost:8000/health
```
**Expected:** `{"role":"Senses","status":"online"}`

### Check Redis
```powershell
docker ps | findstr redis
```
**Expected:** Container `apexsigma.redis.soma` running

---

## Step 3: Execute Meal Trace

```powershell
.\scripts\trace_meal.ps1
```

**Or manual injection:**

```powershell
$payload = @{
    source = "terminal_ghost"
    event_type = "shell_capture"
    payload = @{
        content = "Sean executed the meal trace verification at the Cape Town office yesterday. He confirmed the SimpleMem pipeline is working correctly."
        trace_id = "trace_manual_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        timestamp = (Get-Date -Format "o")
    }
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/manual/ingest" `
    -Method Post `
    -Headers @{ "X-API-Key" = "sigma-dev-secret-key"; "Content-Type" = "application/json" } `
    -Body $payload

Write-Host "✓ Signal captured: $($response.ref)"
$rawLakeId = $response.ref
```

---

## Step 4: Monitor Each Checkpoint

### Checkpoint 1: Postgres (raw_lake)

```sql
-- Run in psql or pgAdmin
SELECT id, source, event_type, processed, ingested_at 
FROM raw_lake 
WHERE source = 'terminal_ghost' 
ORDER BY ingested_at DESC 
LIMIT 1;
```

**Expected:**
- Row exists with UUID from Step 3
- `processed` should change from `FALSE` to `TRUE` after ~5-10 seconds

### Checkpoint 2: InGest Logs (Stomach)

Watch the **Soma.InGest** console window for:

```
digestion_complete    id=<UUID>  entropy=0.85  text_len=123
nervous_system_pulse  stream=soma_working_memory  message_id=<MSG_ID>
```

**Expected:**
- Entropy > 0.35 (passes gate)
- Coreference resolution happened
- Redis XADD successful

### Checkpoint 3: Redis Stream

```powershell
docker exec apexsigma.redis.soma redis-cli -p 6380

# In redis-cli:
XLEN soma_working_memory
XRANGE soma_working_memory - + COUNT 1
```

**Expected:**
- Stream length > 0
- Message contains JSON digest with:
  - `source_id` (raw_lake UUID)
  - `fact_units` array
  - `source: "terminal_ghost"`

### Checkpoint 4: OmegaKG Consumer Logs (Brain)

Watch the **Soma.OmegaKG_Consumer** console window for:

```
processing_digest     message_id=<MSG_ID>  source_id=<UUID>
embedding_generated   model=nomic-embed-text  dimension=768
fact_persisted        node_id=<NEO4J_ID>  entropy=0.85
```

**Expected:**
- Digest parsed successfully
- 768-dim embedding generated
- Neo4j MERGE successful

### Checkpoint 5: Neo4j (Brain Storage)

```cypher
// Run in Neo4j Browser (http://localhost:7474)
MATCH (f:AtomicFact)
WHERE f.source = 'terminal_ghost'
RETURN f.text, f.source_id, f.embedding[0..5] as embedding_sample, f.created_at
ORDER BY f.created_at DESC
LIMIT 1;
```

**Expected AtomicFact node:**
- `.text` = Resolved text (pronouns replaced, "yesterday" → ISO date)
- `.source_id` = raw_lake UUID
- `.embedding` = 768-element array
- `.source` = "terminal_ghost"

### Checkpoint 6: memOS Retrieval (Hands)

Use memOS MCP `query_brain` tool:

```cypher
MATCH (f:AtomicFact)
WHERE f.source = 'terminal_ghost'
RETURN f.text, f.source_id
ORDER BY f.created_at DESC
LIMIT 1
```

**Expected:** Retrieved fact text with:
- Coreference resolved ("Sean" instead of "He")
- Temporal anchoring ("2026-01-26" instead of "yesterday")

---

## Success Criteria (Definition of Done)

✅ **All 6 checkpoints pass**  
✅ **Terminal Ghost signal** travels from InGress → Neo4j  
✅ **SimpleMem Stage 1** active (entropy gate, coreferee, temporal)  
✅ **768-dim embedding** persisted in Neo4j  
✅ **memOS query_brain** retrieves exact fact text

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| InGress won't start | Check port 8000 not in use: `netstat -ano \| findstr :8000` |
| InGest not polling | Check Postgres connection in logs |
| Consumer not reading | Verify Redis Stream exists: `docker exec ... redis-cli XLEN soma_working_memory` |
| No Neo4j nodes | Check Neo4j credentials in consumer logs |
| memOS can't query | Verify Neo4j URI: `bolt://apexsigma.neo4j.soma:7687` |

---

## Log Collection

For detailed analysis, collect logs from all 4 service windows:

1. **InGress** → Copy console output
2. **InGest** → Look for `digestion_complete` events
3. **OmegaKG Consumer** → Look for `fact_persisted` events  
4. **memOS** → MCP server startup logs

Share these if any checkpoint fails.

---

Aweh! 🤙
