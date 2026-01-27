# AGENTS.md - Debug Mode

This file provides guidance to agents when debugging issues in this repository.

## Debug Mode Specific Rules (Non-Obvious Only)

### Hidden Log Locations
- **Extension logs**: Only visible in "Extension Host" output channel, not Debug Console
- **Capture server logs**: Check terminal output where `poetry run capture-server` is running
- **Lifecycle logs**: Use `--dry-run` flag to preview changes without applying

### Silent Failures
- **IPC messages**: Fail silently if not wrapped in try/catch in packages/ipc/src/
- **Production builds**: Require `NODE_ENV=production` or certain features break without error
- **Database migrations**: Must run from packages/evals/ directory, not root

### Required Environment Variables for Debugging
- **OMEGA_ENV**: Must be set correctly (dev|stable|temp) to avoid data corruption
- **NEO4J_URI**: Check connection string format (bolt://localhost:7687 for stable, 7688 for dev, 7689 for temp)
- **OBSIDIAN_VAULT_PATH**: Verify path points to correct vault (./vault for dev/temp, D:/projects/omegavault.as for stable)

### Common Debugging Workflows
- **Extension not capturing**:
  1. Verify capture server running: `curl http://localhost:8765/health`
  2. Reload extension: chrome://extensions → Find Omega_KG → Reload
  3. Check extension logs: chrome://extensions → Omega_KG → Service worker → Inspect
  4. Verify selectors: Open DevTools on supported site → Console → Look for [Omega_KG] log messages

- **Neo4j connection failed**:
  1. Check Neo4j is running: `docker compose ps` or Neo4j Desktop
  2. Verify credentials: `grep NEO4J .env`
  3. Test connection: `poetry run python -c "from neo4j import GraphDatabase; ..."`
  4. Check port conflicts: Ensure correct port (7687/7688/7689) for environment

- **Webhook not working**:
  1. Enable ngrok: Edit .env: `ENABLE_NGROK=true`
  2. Start server (ngrok starts automatically)
  3. Copy ngrok URL from logs
  4. Update Linear webhook URL
  5. Test by creating issue in Linear

### Mock Mode Activation
- **Auto-fallback**: System switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Mock results**: `_get_mock_results()` returns predefined mock lifecycle results (lifecycle.py:231-260)
- **Connection status**: Use `lifecycle.get_connection_status()` to check mock mode state

### Testcontainers Debugging
- **AuthenticationRateLimit**: Exponential backoff required for Python 3.12+ (pytest.ini:147-155)
- **Filter warnings**: DeprecationWarning ignored for Testcontainers compatibility
- **Container cleanup**: Testcontainers automatically cleans up after tests complete

## Mirmir Protocol & memOS MCP Server Integration (Mandatory)

### Debug Mode Specific Retrieval

BEFORE debugging, query memOS MCP for prior debugging sessions:

```python
# Retrieve extension logs from prior debugging sessions
retrieve_context(
    query="extension debugging logs capture server issues",
    limit=10,
    threshold=0.6
)

# Retrieve lifecycle logs and error patterns
retrieve_context(
    query="lifecycle errors Neo4j connection failures",
    limit=5,
    threshold=0.7
)

# Query for similar issues and their resolutions
retrieve_context(
    query="debug workflow extension not capturing solutions",
    limit=5,
    threshold=0.6
)
```

### Recording Debugging Discoveries

After resolving debugging issues, record to memOS MCP:

```python
# Record debugging solution
mark_significant(
    session_id="debug-session",
    content="Fixed Neo4j connection by ensuring correct port mapping: stable=7687, dev=7688, temp=7689",
    significance=0.85,
    reason="Prevents future connection issues across environments"
)

# Record debugging steps
scratch_write(
    session_id="debug-session",
    content="Debug workflow: curl health check → reload extension → check service worker logs → verify selectors",
    metadata={"workflow": True, "component": "extension"}
)

# Promote after completing debugging session
promote_memory(session_id="debug-session", memory_id="pending-id")
```

**Required recording triggers in Debug Mode:**
- After resolving any error or bug
- When discovering new debugging techniques
- When finding hidden log locations
- When encountering silent failures
- After completing debugging workflows

### Debugging Knowledge Cache
- **Extension logs**: Record patterns for extension debugging
- **Capture server logs**: Document server-side debugging insights
- **Lifecycle logs**: Track error patterns and resolutions
- **Environment-specific issues**: Note differences across dev/stable/temp