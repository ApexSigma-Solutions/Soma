# AGENTS.md - Code Mode

This file provides guidance to agents when writing code in this repository.

## Code Mode Specific Rules (Non-Obvious Only)

### Critical Coding Patterns
- **Neo4j context managers mandatory**: Always use `async with graph_driver.session() as session:` pattern or will leak connections (capture_server.py:307)
- **AsyncGraphDriver for non-blocking**: Use AsyncGraphDriver from omega_kg.database.graph for async operations (capture_server.py:141)
- **UTF-8 encoding required**: Always use `encoding="utf-8"` for file operations (capture_server.py:355, lifecycle.py:366)
- **Platform sanitization**: Apply regex `r'[<>:"|?*\x00-\x1f]'` before folder creation (capture_server.py:327)

### File Path Conventions
- **AI_Conversations**: Hardcoded `AI_Conversations/{platform}/` folder in Obsidian vault (capture_server.py:339)
- **Task file discovery**: Use glob pattern `f"Tasks/**/{uid}*.md"` for finding task files (lifecycle.py:358)
- **Content ID format**: Use `CAP-{YYYYMMDD}-{HASH}` for conversation frontmatter IDs (capture_server.py:225)

### Database Operations
- **Dual persistence**: Tasks stored in both Neo4j AND Obsidian markdown files with frontmatter sync (lifecycle.py:317-391)
- **Write-behind pattern**: ChatSession nodes queue embeddings via `store_pending()` then process asynchronously (capture_server.py:520-526)
- **Health check pattern**: Use `RETURN 1` query for Neo4j connection validation (capture_server.py:667)

### Security & Authentication
- **JWT exchange flow**: Chrome extension exchanges static API key for short-lived JWT tokens (capture_server.py:695-716)
- **CORS exact match**: Extension ID must match exactly in CORS configuration (capture_server.py:138)
- **Bitwarden priority**: Bitwarden SDK → Environment variables (.env) → Defaults (settings.py:267-272)

### Async Patterns
- **APScheduler fallback**: Dummy class provided when APScheduler not available (capture_server.py:57-68)
- **Embedding worker**: Polls every 10 seconds for pending embeddings (capture_server.py:75-76)
- **Session scheduler**: Batch percolation runs every 5 minutes via APScheduler (capture_server.py:84-88)

### Mock Mode Handling
- **Auto-fallback**: System switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Mock results**: `_get_mock_results()` returns predefined mock lifecycle results (lifecycle.py:231-260)

### Testing Patterns
- **Test markers**: Use `@pytest.mark.requires_neo4j` for database-dependent tests
- **Mock fixtures**: `mock_env_vars`, `mock_neo4j_driver`, `task_lifecycle_mock` from conftest.py
- **Test vault**: Tests automatically create `./test_vault` directory structure

## Mirmir Protocol & memOS MCP Server Integration (Mandatory)

### Recording Requirements for Code Mode

After any significant coding action, record to memOS MCP:

```python
# Record code pattern discoveries
mark_significant(
    session_id="current-session",
    content="Discovered Neo4j context manager leak pattern in capture_server.py:307",
    significance=0.9,
    reason="Prevents connection pool exhaustion in production"
)

# Record architectural decisions
scratch_write(
    session_id="current-session",
    content="Decision: Using AsyncGraphDriver for all Neo4j operations to prevent blocking",
    metadata={"decision": True, "component": "database"}
)

# Promote after completing implementation
promote_memory(session_id="current-session", memory_id="pending-id")
```

**Required recording triggers in Code Mode:**
- After resolving any error or bug
- When discovering non-obvious patterns
- After architectural decisions
- When encountering configuration gotchas
- Before modifying core systems (`domain/linear`, `omega_kg`)
- After completing significant tasks

### Retrieval Before Coding

BEFORE writing code, query memOS MCP:

```python
# Check for existing patterns
retrieve_context(
    query="Neo4j connection context manager async patterns",
    limit=5,
    threshold=0.7
)

# Get related concepts
get_concepts(concept_id="database-connections", depth=2)
```

### Environment-Specific Memory Handling
- **Omega_KG_dev (ephemeral)**: Promote critical code discoveries before environment termination
- **Omega_KG_stable (persistent)**: Build upon cached patterns
- **omega_kg_temp (testing)**: Leverage cached patterns while contributing new discoveries