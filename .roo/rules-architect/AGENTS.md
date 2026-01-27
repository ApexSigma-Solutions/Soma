# AGENTS.md - Architect Mode

This file provides guidance to agents when planning architecture for this repository.

## Architect Mode Specific Rules (Non-Obvious Only)

### Multi-Environment Architecture
- **Three separate environments**: Omega_KG_dev/ (ephemeral), Omega_KG_stable/ (persistent), omega_kg_temp/ (testing)
- **Vault isolation**: Dev/temp use ./vault (local), stable uses D:/projects/omegavault.as (external shared)
- **Port mapping**: Different Neo4j ports per environment (7687 stable, 7688 dev, 7689 temp)

### Hidden Coupling
- **Monorepo circular dependency**: Packages have circular dependency on types package (intentional)
- **Dual database strategy**: Neo4j for graph relationships, PostgreSQL for events/vectors (pgvector)
- **Write-behind pattern**: Immediate capture to Obsidian + Neo4j, async embedding generation

### Undocumented Architectural Decisions
- **APScheduler dummy class**: Graceful degradation when APScheduler not available (capture_server.py:57-68)
- **Mock mode fallback**: Auto-switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Ollama auto-start**: Capture server starts Ollama as subprocess if not running (capture_server.py:372-412)

### Configuration Gotchas
- **OMEGA_ENV marker**: Must be correct in all .env files to prevent data corruption
- **Zero-trust enforcement**: Missing Bitwarden secret IDs cause hard failures in stable environment (settings.py:246-252)
- **Testcontainers warnings**: Filterwarnings ignore DeprecationWarning for Python 3.12+ compatibility (pytest.ini:147-155)

### Task Lifecycle Rules
- **Draft → Archived**: 14 days (auto), 10 days (warn) unless pinned (lifecycle.py:63-77)
- **Active → Blocked**: 30 days without commits (lifecycle.py:79-85)
- **Completed → Archived**: 90 days (lifecycle.py:87-92)

## Mirmir Protocol & memOS MCP Server Integration (Mandatory)

### Architectural Decision Recording

When making architectural decisions, record to memOS MCP:

```python
# Record architectural decision with full context
mark_significant(
    session_id="architect-session",
    content="Decision: Dual persistence strategy using Neo4j for graph + Obsidian for markdown files with frontmatter sync",
    significance=0.95,
    reason="Ensures data durability while maintaining graph relationships and human-readable records"
)

# Record coupling and dependencies
scratch_write(
    session_id="architect-session",
    content="Architectural constraint: Monorepo has intentional circular dependency on types package",
    metadata={"constraint": True, "type": "coupling"}
)

# Record environment-specific considerations
scratch_write(
    session_id="architect-session",
    content="Environment architecture: Omega_KG_dev ephemeral, Omega_KG_stable persistent, omega_kg_temp testing",
    metadata={"architecture": True, "environments": ["dev", "stable", "temp"]}
)

# Promote after completing architectural work
promote_memory(session_id="architect-session", memory_id="pending-id")
```

**Required recording triggers in Architect Mode:**
- When making architectural decisions
- When discovering hidden coupling or dependencies
- When documenting undocumented decisions
- When planning multi-environment strategies
- When defining configuration requirements
- Before modifying core systems

### Retrieval Before Architectural Planning

BEFORE planning architecture, query memOS MCP:

```python
# Retrieve prior architectural decisions
retrieve_context(
    query="architectural decisions dual persistence Neo4j Obsidian",
    limit=10,
    threshold=0.7
)

# Retrieve environment-specific patterns
retrieve_context(
    query="multi-environment architecture vault isolation configuration",
    limit=5,
    threshold=0.7
)

# Retrieve constraints and gotchas
get_concepts(
    concept_id="architectural-constraints",
    depth=2
)
```

### Knowledge Cache for Architecture
- **Architectural decisions**: Record rationale and trade-offs
- **Environmental patterns**: Document multi-environment considerations
- **Coupling dependencies**: Track hidden relationships
- **Configuration requirements**: Preserve environment-specific settings
- **Lifecycle automation**: Document task state transitions

### Mirmir Protocol Constraints (Mandatory)

Before proposing architectural changes, consult the Codex:

```python
# Check for historical failures and constraints
get_constraints(
    action_type="architectural_change",
    context_tags=["architecture", "multi-environment", "database"]
)

# Verify implementation against Mimir constraints
verify_implementation(
    plan_text="Proposed architectural change description",
    implementation_diff="Expected implementation approach"
)
```

**Format for Codex entries:**
"CONTEXT: [Architectural situation]. DECISION: [What was decided]. RATIONALE: [Why]. CONSTRAINT: [Rule to maintain]. ENVIRONMENT: [dev/stable/temp]"