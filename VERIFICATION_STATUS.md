# Soma E2E Verification Status

## Current Status: ⚠️ Blocked - Environment Setup Needed

### Issues Encountered

1. **Orchestrator Dependency**: Missing `structlog` in root Python environment
2. **Poetry Not in PATH**: Services expect Poetry for virtual environment management  
3. **Services Not Running**: InGress, InGest, OmegaKG consumer need to be started

---

## Code Readiness: ✅ 100% Complete

| Component | Status | File |
|-----------|--------|------|
| InGress Endpoint | ✅ Ready | [main.py](file:///d:/projects/Soma/InGress/soma_ingress/main.py) |
| SimpleMem Stomach | ✅ Ready | [raw_lake_poller_v2.py](file:///d:/projects/Soma/InGest/ingest/raw_lake_poller_v2.py) |
| OmegaKG Consumer | ✅ Ready | [consumer.py](file:///d:/projects/Soma/OmegaKG/omega_kg/consumer.py) |
| Verification Script | ✅ Ready | [trace_meal.ps1](file:///d:/projects/Soma/scripts/trace_meal.ps1) |

---

## Manual Startup Instructions

### Option 1: Individual Terminals

```powershell
# Terminal 1: InGress (Senses)
cd d:\projects\Soma\InGress
poetry run uvicorn soma_ingress.main:app --host 0.0.0.0 --port 8000

# Terminal 2: InGest (Stomach)  
cd d:\projects\Soma\InGest
poetry run python ingest/raw_lake_poller_v2.py

# Terminal 3: OmegaKG Consumer (Brain)
cd d:\projects\Soma\OmegaKG
poetry run python -m omega_kg.consumer

# Terminal 4: Run Trace
cd d:\projects\Soma
.\scripts\trace_meal.ps1
```

### Option 2: Fix Orchestrator

```powershell
# Install structlog at root
pip install structlog

# Then run orchestrator
cd d:\projects\Soma
python orchestrator.py
```

---

## Manual Verification Checklist

Once services are running, verify each checkpoint:

### 1. InGress (Senses)
```powershell
curl -X POST http://localhost:8000/api/v1/manual/ingest `
  -H "X-API-Key: sigma-dev-secret-key" `
  -H "Content-Type: application/json" `
  -d '{"source":"test","event_type":"verification","payload":{"message":"Test signal"}}'
```
**Expected:** `{"status":"captured","ref":"<UUID>"}`

### 2. Postgres (raw_lake)
```sql
SELECT id, source, processed FROM raw_lake 
WHERE source = 'test' 
ORDER BY ingested_at DESC 
LIMIT 1;
```
**Expected:** Row with `processed=FALSE` initially

### 3. InGest (SimpleMem)
Check InGest logs for:
- `digestion_complete` event
- `nervous_system_pulse` event (Redis XADD)

### 4. Redis Stream
```bash
redis-cli -p 6380
XLEN soma_working_memory
XRANGE soma_working_memory - + COUNT 1
```
**Expected:** Stream length > 0, message with digest payload

### 5. OmegaKG Consumer
Check consumer logs for:
- `processing_digest` event
- `embedding_generated` event  
- `fact_persisted` event

### 6. Neo4j (Brain)
```cypher
MATCH (f:AtomicFact)
WHERE f.source = 'test'
RETURN f.text, f.source_id, f.embedding
ORDER BY f.created_at DESC
LIMIT 1
```
**Expected:** AtomicFact node with:
- `.text` (resolved content)
- `.source_id` (raw_lake UUID)
- `.embedding` (768-dim array)

### 7. memOS (Hands)
Use `query_brain` tool:
```cypher
MATCH (f:AtomicFact)
WHERE f.source = 'test'
RETURN f.text
LIMIT 1
```
**Expected:** Retrieved fact text

---

## Next Steps

1. Start services manually (I cannot auto-run in your environment)
2. Run `trace_meal.ps1` OR follow manual checklist above
3. Report back with results and I'll provide detailed analysis
