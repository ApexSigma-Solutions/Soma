# memOS.MCP Debugging Session

## Issue
memOS.MCP server not operational despite Docker infrastructure running

## Root Cause
Port configuration mismatch in `.mcp.json`

## Infrastructure Status (All Running ✓)
- Redis: memos-redis-mcp on port **6380** (not 6379)
- PostgreSQL: apexsigma.postgres.stable on port **6000** (not 5800)
- Neo4j: apexsigma.neo4j.stable on port **7687** ✓
- Ollama: Running on host port **11434** ✓

## Fixes Applied

### 1. Updated .mcp.json Configuration
**Changed**:
- POSTGRES_PORT: 5800 → **6000**
- POSTGRES_DB: omega_kg → **omega_kg_stable**
- REDIS_PORT: 6379 → **6380**
- POSTGRES_USER: ${POSTGRES_USER} → **omega_user**
- POSTGRES_PASSWORD: ${POSTGRES_PASSWORD} → **omega_dev_password**

**Added**:
- POSTGRES_SCHEMA: **memos**
- EMBEDDING_MODEL: **bge-m3:latest**
- EMBEDDING_DIMENSION: **1024**
- NEO4J_PASSWORD: Actual password

### 2. Updated Verification Script
- Updated service check commands to use correct ports
- Changed to use docker exec commands for reliability

### 3. Tool Parameter Corrections
**mark_significant** requires:
- session_id
- content
- **significance** (float 0-1) - was missing!
- reason

**promote_memory** requires:
- session_id
- **memory_id** (from mark_significant return) - was missing!

## Verification Results
After fixes:
- ✓ .mcp.json valid
- ✓ Redis running (6380)
- ✓ PostgreSQL running (6000)
- ✓ Neo4j running (7687) - verified via docker exec
- ✓ Ollama running (11434)
- ✓ Config loads correctly
- ✓ PGVector store initializes
- ✓ MCP server imports successfully

## Documentation Created
- docs/MCP_DEBUG_REPORT.md - Full debugging findings
- Updated scripts/verify_mcp_config.py - Correct ports

## Next Steps for User
1. **Reload Claude Code window** - Pick up new .mcp.json
2. **Ask "What MCP tools are available?"** - Verify tools loaded
3. **Test memOS tools** - Try with correct parameters

## Lessons Learned
- Docker port mappings can differ from defaults
- Environment variable substitution in .mcp.json may not work as expected
- Always verify actual port mappings: `docker ps`
- Tool parameter requirements must match exact signatures

## Status
✅ RESOLVED - All infrastructure operational, configuration corrected
