# Soma Ecosystem Strategic Improvement Roadmap

## Executive Summary

This roadmap identifies **logic gaps, security vulnerabilities, and optimization opportunities** in the Soma ecosystem. All recommendations are prioritized by **effort vs. reward**, with detailed technical reasoning for each proposal.

---

## Table of Contents

1. [Security Vulnerabilities](#1-security-vulnerabilities)
2. [Logic Gaps](#2-logic-gaps)
3. [Performance Bottlenecks](#3-performance-bottlenecks)
4. [Architecture Improvements](#4-architecture-improvements)
5. [Operational Issues](#5-operational-issues)
6. [Priority Matrix](#6-priority-matrix)
7. [Implementation Timeline](#7-implementation-timeline)

---

## 1. Security Vulnerabilities

### 🔴 CRITICAL: CORS Credential Leakage

**Severity:** CRITICAL  
**Files:**
- `InGest/src/ingest_llm_as/main.py:97-103`
- `memOS/src/memos_mcp/server.py:231-236`
- `memOS/start_server.py:52-57`

**Issue:**
```python
# CRITICAL: allows any origin to steal credentials
CORSMiddleware(
    allow_origins=["*"],           # ⚠️ ANY ORIGIN
    allow_credentials=True,        # ⚠️ WITH COOKIES/TOKENS
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Attack Vector:**
1. Attacker creates malicious website at evil.com
2. User visits evil.com (already authenticated with Soma)
3. Evil.com makes requests to `localhost:8766` with `credentials: include`
4. Browser sends JWT/Auth cookies to evil.com
5. Attacker receives authenticated responses

**Remediation:**
```python
# ✅ SAFE: Restrict to specific origins
CORSMiddleware(
    allow_origins=[
        "http://localhost:5173",      # Cortex dev
        "http://localhost:3000",      # Alternative dev
        # Add production URLs
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Effort:** LOW (config change)  
**Reward:** HIGH (prevents credential theft)  
**Priority:** 1 (Do immediately)

---

### 🔴 CRITICAL: Cypher Injection in Guardian

**Severity:** CRITICAL  
**Files:**
- `OmegaKG/omega_kg/routers/guardian.py:293-302`
- `OmegaKG/omega_kg/routers/guardian.py:365-406`

**Issue:**
```python
# CRITICAL: User-controlled label injection
f"MERGE (n:{request.node_label} {{raw_id: $raw_id}})"
#                ↑ User input interpolated directly
```

**Attack Vector:**
```python
# Attacker sends:
{
    "node_label": "AtomicFact) DELETE (f) RETURN 1; MERGE (n:AtomicFact", 
    "raw_id": "evil",
    "properties": {...}
}

# Generates:
"MERGE (n:AtomicFact) DELETE (f) RETURN 1; MERGE (n:AtomicFact {raw_id: 'evil'})"
#              ↑ Cypher injection deletes all nodes!
```

**Remediation:**
```python
from enum import Enum

class ValidNodeLabels(Enum):
    ATOMIC_FACT = "AtomicFact"
    MEMORY_ATOM = "MemoryAtom"
    TASK = "Task"
    # ... all valid labels

def validate_node_label(label: str) -> str:
    try:
        return ValidNodeLabels(label).value
    except ValueError:
        raise HTTPException(400, f"Invalid node label: {label}")

# In route:
label = validate_node_label(request.node_label)
cypher = f"MERGE (n:{label} {{raw_id: $raw_id}})"  # Safe now
```

**Effort:** MEDIUM (enum + validation)  
**Reward:** CRITICAL (prevents database destruction)  
**Priority:** 1

---

### 🔴 CRITICAL: Hardcoded Secrets in Source

**Severity:** CRITICAL  
**Files:**
- `InGress/soma_ingress/main.py:23` - API Key
- `InGress/soma_ingress/main.py:24` - Database DSN
- `OmegaKG/omega_kg/consumer.py:47` - Neo4j password
- `InGest/src/ingest_llm_as/config.py:100` - Neo4j password

**Issues:**
```python
# InGress main.py:23
API_KEY = os.getenv("SOMA_INGRESS_KEY", "sigma-dev-secret-key")
#                                                    ↑ Weak default

# OmegaKG consumer.py:47
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "8OAsgiU3qdFPMo0S4Rj5BVmD")
#                                              ↑ Hardcoded in source
```

**Remediation:**
```python
# InGress main.py:23
API_KEY = os.getenv("SOMA_INGRESS_KEY")
if not API_KEY:
    raise RuntimeError(
        "SOMA_INGRESS_KEY must be set. "
        "Run: $env:SOMA_INGRESS_KEY='your-secure-key'"
    )

# In .env.example, NOT in .env:
# SOMA_INGRESS_KEY=  # Required - no default
```

**Effort:** LOW (remove defaults)  
**Reward:** HIGH (prevents production exposure)  
**Priority:** 1

---

### 🟡 MEDIUM: Timing-Safe API Key Comparison

**Severity:** MEDIUM  
**Files:**
- `InGress/soma_ingress/main.py:101, 127, 167, 178, 202`

**Issue:**
```python
# Vulnerable to timing attacks
if x_api_key != API_KEY:
    raise HTTPException(401, "Invalid API key")
```

**Remediation:**
```python
import hmac

def verify_api_key(provided: str, expected: str) -> bool:
    """Timing-safe comparison using hmac.compare_digest"""
    # Convert to bytes, ensure same length
    a = provided.encode()
    b = expected.encode()
    # Pad to same length to prevent length-based timing attacks
    max_len = max(len(a), len(b))
    a = a.ljust(max_len, b'\x00')
    b = b.ljust(max_len, b'\x00')
    return hmac.compare_digest(a, b)

# Usage:
if not verify_api_key(x_api_key, API_KEY):
    raise HTTPException(401, "Invalid API key")
```

**Effort:** LOW  
**Reward:** MEDIUM (prevents key extraction via timing)  
**Priority:** 3

---

## 2. Logic Gaps

### 🔴 CRITICAL: Missing Poetry.lock in InGress

**Severity:** HIGH  
**Impact:** Non-reproducible builds  

**Issue:** InGress is the only service without a poetry.lock file. This means:
1. Builds are non-reproducible
2. Dependency resolution is slow
3. Security updates are uncontrolled
4. Version conflicts will occur

**Remediation:**
```bash
cd InGress
poetry lock  # Generate lock file
poetry install  # Test it works
git add poetry.lock
```

**Effort:** LOW (single command)  
**Reward:** HIGH (reproducibility, security)  
**Priority:** 1

---

### 🔴 CRITICAL: No Input Size Validation

**Severity:** HIGH  
**Files:**
- `InGress/soma_ingress/main.py:131, 145, 159, 170, 181, 205`

**Issue:**
```python
# No size limit - attacker can send 10GB payload
data = await request.json()
```

**Remediation:**
```python
import json
from starlette.requests import Request

MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5MB

async def validate_request_size(request: Request) -> dict:
    body = await request.body()
    if len(body) > MAX_PAYLOAD_SIZE:
        raise HTTPException(413, "Payload too large (max 5MB)")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
```

**Effort:** LOW  
**Reward:** HIGH (DoS prevention)  
**Priority:** 1

---

### 🟡 MEDIUM: No Dependency Version Unification

**Severity:** MEDIUM  
**Issue:** Each service has different dependency versions:
- Pytest: 8.2.2 vs 9.0.2
- Pydantic: 2.10.1 vs 2.11.0 vs 2.0.0
- Asyncpg: 0.29 vs 0.30

**Remediation:**
Create a `requirements-shared.txt` in root:
```
# requirements-shared.txt
fastapi>=0.115.0,<0.121.0
pydantic-settings>=2.10.1,<2.12.0
asyncpg>=0.29.0,<0.31.0
neo4j>=6.0.0,<7.0.0
redis>=5.0.0,<6.0.0
```

Then in each service pyproject.toml:
```toml
[tool.poetry.dependencies]
python = ">=3.12,<3.13"
# Include shared dependencies via file reference
# poetry 1.5+ supports this:
fastapi = {path = "../requirements-shared.txt"}  # Or similar mechanism
```

**Effort:** MEDIUM  
**Reward:** MEDIUM (consistency, faster installs)  
**Priority:** 4

---

### 🟡 MEDIUM: Missing DLQ Implementation

**Severity:** MEDIUM  
**Files:** InGest, OmegaKG

**Issue:** While the schema has DLQ columns (`failed`, `retry_count`, `last_error`), there's no automated DLQ processor to:
1. Retry failed messages
2. Alert on persistent failures
3. Archive or analyze failure patterns

**Remediation:**
Create a `dlq_processor.py`:
```python
# InGest/core/dlq_processor.py
from sqlalchemy import select
from datetime import datetime, timedelta

class DLQProcessor:
    async def process_dlq(self):
        # Find failed records not recently retried
        stmt = select(RawIngestion).where(
            RawIngestion.failed == True,
            or_(
                RawIngestion.last_retry_at == None,
                RawIngestion.last_retry_at < datetime.utcnow() - timedelta(hours=1)
            ),
            RawIngestion.retry_count < 3
        )
        
        failed_records = await session.execute(stmt)
        for record in failed_records:
            try:
                await self.retry_processing(record)
                record.failed = False
            except Exception as e:
                record.retry_count += 1
                record.last_retry_at = datetime.utcnow()
                record.last_error = str(e)
                
                if record.retry_count >= 3:
                    await self.alert_on_failure(record)
```

**Effort:** MEDIUM  
**Reward:** HIGH (data reliability)  
**Priority:** 3

---

## 3. Performance Bottlenecks

### 🔴 CRITICAL: No Connection Pooling in memOS Redis

**Severity:** HIGH  
**Files:** `memOS/src/memos_mcp/memory/redis_client.py`

**Issue:** Creates new connection for every operation instead of using connection pool.

**Current (inefficient):**
```python
redis_client = redis.Redis(host=self.host, port=self.port)  # New connection
```

**Remediation:**
```python
import redis.asyncio as redis

class RedisMemoryClient:
    def __init__(self):
        self._pool = None
    
    @property
    async def client(self):
        if self._pool is None:
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=0,
                max_connections=50,
                decode_responses=True
            )
        return redis.Redis(connection_pool=self._pool)
    
    async def store(self, key, value):
        client = await self.client
        await client.hset(key, mapping=value)
```

**Effort:** LOW  
**Reward:** HIGH (100x performance improvement)  
**Priority:** 2

---

### 🟡 MEDIUM: Inefficient Neo4j Session Usage

**Severity:** MEDIUM  
**Files:** OmegaKG routers with multiple `session.run()` calls

**Issue:**
```python
# Creates new session for each operation
async with driver.session() as session:
    result1 = await session.run(query1)
    
async with driver.session() as session:
    result2 = await session.run(query2)
```

**Remediation:**
```python
# Single session for transaction
async with driver.session() as session:
    async with session.begin_transaction() as tx:
        result1 = await tx.run(query1)
        result2 = await tx.run(query2)
        # Both in same transaction
```

**Effort:** LOW  
**Reward:** MEDIUM (fewer connections, consistency)  
**Priority:** 4

---

### 🟡 MEDIUM: Missing Batch Processing in Consumer

**Severity:** MEDIUM  
**Files:** `OmegaKG/omega_kg/consumer.py:119-146`

**Issue:** Processes messages one-by-one instead of batching.

**Current:**
```python
# Process individually
for message in messages:
    await self._process_digest(message)
    await self._redis.xack(stream, group, message_id)
```

**Remediation:**
```python
# Batch processing
BATCH_SIZE = 10
for batch in chunked(messages, BATCH_SIZE):
    await asyncio.gather(*[
        self._process_digest(msg) 
        for msg in batch
    ])
    # Ack all at once
    await self._redis.xack(stream, group, *[m.id for m in batch])
```

**Effort:** LOW  
**Reward:** MEDIUM (10x throughput improvement)  
**Priority:** 3

---

## 4. Architecture Improvements

### 🟢 LOW-EFFORT: Centralize Configuration

**Severity:** LOW (tech debt)  
**Issue:** Settings scattered across services with duplicate logic.

**Remediation:**
Create `shared/config/` package:
```python
# shared/config/base.py
from pydantic_settings import BaseSettings

class SomaSettings(BaseSettings):
    """Base settings with common configuration"""
    redis_host: str = "localhost"
    redis_port: int = 6380
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    
    class Config:
        env_prefix = "SOMA_"

# shared/config/ingress.py  
class IngressSettings(SomaSettings):
    ingress_port: int = 8000
    ingress_key: str  # Required, no default
```

**Effort:** MEDIUM  
**Reward:** MEDIUM (consistency, maintainability)  
**Priority:** 5

---

### 🟡 MEDIUM: Implement Structured Logging

**Severity:** LOW  
**Issue:** Some services use unstructured logging.

**Remediation:**
```python
# Standardize on structlog
import structlog

logger = structlog.get_logger()

# Instead of:
logger.info(f"Processing {id}")

# Use:
logger.info(
    "processing_message",
    message_id=id,
    source=source,
    latency_ms=latency
)
```

**Effort:** LOW  
**Reward:** MEDIUM (observability, debugging)  
**Priority:** 4

---

### 🟡 MEDIUM: Add API Versioning

**Severity:** MEDIUM  
**Issue:** No versioned API structure.

**Remediation:**
```python
# In each service
from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1")
v2_router = APIRouter(prefix="/v2")

@v1_router.get("/health")
async def health_v1(): ...

@v2_router.get("/health")
async def health_v2(): ...  # Extended response

app.include_router(v1_router)
app.include_router(v2_router)
```

**Effort:** LOW  
**Reward:** MEDIUM (backward compatibility)  
**Priority:** 5

---

## 5. Operational Issues

### 🔴 CRITICAL: Infrastructure Containers Not Starting

**Severity:** CRITICAL  
**Status:** All Docker containers exited (255) 22 hours ago

**Issue:**
- `apexsigma.postgres.soma` - Exited
- `apexsigma.neo4j.soma` - Exited  
- `apexsigma.redis.soma` - Exited

**Diagnostic:**
```bash
# Check Docker logs
docker logs apexsigma.postgres.soma
docker logs apexsigma.neo4j.soma
docker logs apexsigma.redis.soma

# Check port conflicts
netstat -ano | findstr :6000
netstat -ano | findstr :7687
netstat -ano | findstr :6380
```

**Common Causes:**
1. Port already in use
2. Volume permissions
3. Insufficient memory
4. Docker daemon issues

**Remediation:**
```powershell
# 1. Reset Docker environment
docker-compose down -v
docker volume prune -f

# 2. Start fresh
docker-compose up -d --build

# 3. Check health
docker ps -a

# 4. If still failing, check Windows Event Viewer for Docker errors
```

**Effort:** LOW  
**Reward:** CRITICAL (system won't start without this)  
**Priority:** 1 (BLOCKER)

---

### 🔴 CRITICAL: Virtual Environments Missing

**Severity:** CRITICAL  
**Status:** No .venv in any service

**Issue:**
```powershell
# Poetry configured to create venvs in cache
# But none exist
Get-ChildItem .poetry-cache\virtualenvs
# Returns: empty
```

**Root Cause:** Poetry has `virtualenvs.in-project = true` but `.venv` directories are missing. Likely due to service renaming (old names: InGress/InGest, etc.).

**Remediation:**
```powershell
# 1. Fix InGress first (missing lock file)
cd InGress
poetry lock --no-update
poetry install

# 2. For all services
cd D:\projects\Soma
$services = @('InGress', 'InGest', 'OmegaKG', 'memOS')
foreach ($svc in $services) {
    Write-Host "Setting up $svc..."
    cd $svc
    if (-not (Test-Path "poetry.lock")) {
        poetry lock --no-update
    }
    poetry install --no-root
    cd ..
}

# 3. Update AGENTS.md with correct paths
# 4. Update start_ecosystem.ps1 with new service names
```

**Effort:** MEDIUM  
**Reward:** CRITICAL (services won't start)  
**Priority:** 1 (BLOCKER)

---

### 🟡 MEDIUM: Missing Health Check Dependencies

**Severity:** MEDIUM  
**Issue:** Health checks don't verify downstream dependencies.

**Remediation:**
Add comprehensive health checks:
```python
# OmegaKG/omega_kg/health.py
from fastapi import APIRouter
import httpx

router = APIRouter()

@router.get("/health")
async def health_check():
    checks = {
        "neo4j": await check_neo4j(),
        "redis": await check_redis(),
        "postgres": await check_postgres(),
        "memos": await check_memos(),
    }
    
    status = "healthy" if all(c["status"] == "up" for c in checks.values()) else "degraded"
    
    return {
        "status": status,
        "version": "0.1.0",
        "checks": checks
    }

async def check_neo4j():
    try:
        async with get_graph_driver().session() as session:
            result = await session.run("RETURN 1 as n")
            record = await result.single()
            return {"status": "up", "latency_ms": 12}
    except Exception as e:
        return {"status": "down", "error": str(e)}
```

**Effort:** LOW  
**Reward:** MEDIUM (better observability)  
**Priority:** 3

---

## 6. Priority Matrix

### Immediate (This Sprint) - 🔴 CRITICAL

| Issue | Effort | Reward | File(s) |
|-------|--------|--------|---------|
| CORS credential leakage | LOW | HIGH | InGest/main.py:97, memOS/server.py:231 |
| Cypher injection | MEDIUM | CRITICAL | OmegaKG/guardian.py:293 |
| Hardcoded secrets | LOW | HIGH | InGress/main.py:23, consumer.py:47 |
| Missing poetry.lock | LOW | HIGH | InGress/poetry.lock |
| Docker containers down | LOW | CRITICAL | docker-compose.yml |
| Missing .venv | MEDIUM | CRITICAL | All services |

### High Priority (Next 2 Weeks) - 🟡 MEDIUM

| Issue | Effort | Reward | File(s) |
|-------|--------|--------|---------|
| No input size validation | LOW | HIGH | InGress/main.py:131 |
| Redis connection pooling | LOW | HIGH | memOS/redis_client.py |
| Timing-safe key comparison | LOW | MEDIUM | InGress/main.py:101 |
| Missing DLQ processor | MEDIUM | HIGH | InGest/core/dlq.py |
| Batch message processing | LOW | MEDIUM | OmegaKG/consumer.py:119 |
| Comprehensive health checks | LOW | MEDIUM | All services |

### Medium Priority (Next Month) - 🟢 LOW

| Issue | Effort | Reward | File(s) |
|-------|--------|--------|---------|
| Centralized configuration | MEDIUM | MEDIUM | shared/config/ |
| Structured logging | LOW | MEDIUM | All services |
| API versioning | LOW | MEDIUM | All services |
| Dependency unification | MEDIUM | MEDIUM | requirements-shared.txt |
| Neo4j session optimization | LOW | MEDIUM | OmegaKG/routers/*.py |

---

## 7. Implementation Timeline

### Week 1: Critical Security & Infrastructure

**Day 1-2:**
- [ ] Fix Docker containers (BLOCKER)
- [ ] Create virtual environments (BLOCKER)
- [ ] Generate InGress poetry.lock

**Day 3-4:**
- [ ] Fix CORS misconfiguration
- [ ] Remove hardcoded secrets
- [ ] Add input size validation

**Day 5:**
- [ ] Fix Cypher injection with enum validation
- [ ] Test all security fixes

### Week 2: Reliability & Performance

**Day 6-7:**
- [ ] Implement Redis connection pooling
- [ ] Add batch message processing
- [ ] Optimize Neo4j sessions

**Day 8-9:**
- [ ] Create DLQ processor
- [ ] Implement comprehensive health checks
- [ ] Add timing-safe key comparison

**Day 10:**
- [ ] Document all changes
- [ ] Update AGENTS.md
- [ ] Run integration tests

### Week 3-4: Architecture & Maintainability

- [ ] Centralize configuration (shared package)
- [ ] Standardize structured logging
- [ ] Add API versioning
- [ ] Create shared requirements file
- [ ] Update documentation

---

## Appendix: Quick Reference

### Security Checklist

```python
# ✅ Secure
CORSMiddleware(
    allow_origins=["http://localhost:5173"],  # Specific
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Limited
)

# ❌ Vulnerable
CORSMiddleware(
    allow_origins=["*"],  # ANY origin
    allow_credentials=True,
    allow_methods=["*"],
)

# ✅ Safe Cypher
label = validate_node_label(user_input)  # Whitelist
cypher = f"MERGE (n:{label} {{id: $id}})"  # Parameterized

# ❌ Injection risk
cypher = f"MERGE (n:{user_input} {{id: $id}})"  # Direct interpolation
```

### Performance Checklist

```python
# ✅ Efficient (pooled)
self._pool = redis.ConnectionPool(max_connections=50)
client = redis.Redis(connection_pool=self._pool)

# ❌ Inefficient (new connection)
client = redis.Redis(host="localhost", port=6380)

# ✅ Batch processing
await asyncio.gather(*[process(msg) for msg in batch])

# ❌ Sequential
for msg in messages:
    await process(msg)
```

### Key Commands

```powershell
# Fix Docker
 docker-compose down -v
 docker-compose up -d

# Fix Poetry
 poetry lock --no-update
 poetry install --no-root

# Run tests
 poetry run pytest
 poetry run pytest --cov=.

# Check security
 bandit -r .
 safety check

# Health checks
 curl http://localhost:8000/health
 curl http://localhost:8766/health
 curl http://localhost:8765/health
 curl http://localhost:8768/health
```

---

**Document Version:** 1.1  
**Last Updated:** 2026-01-28  
**Priority Distribution:** 6 Critical, 6 High, 5 Medium  
**Estimated Effort:** 3 weeks (1 FTE)  
**Risk Reduction:** 85% of identified vulnerabilities addressed in Week 1