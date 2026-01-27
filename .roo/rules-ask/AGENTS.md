# AGENTS.md - Ask Mode

This file provides guidance to agents when answering questions about this repository.

## Ask Mode Specific Rules (Non-Obvious Only)

### Counterintuitive Code Organization
- **Multi-environment structure**: Three separate directories (Omega_KG_dev/, Omega_KG_stable/, omega_kg_temp/) with different configurations
- **Main development in omega_kg_temp/**: Most active development happens here, not in root
- **Shared vault**: omegavault.as/ is shared with stable only, dev/temp use local ./vault

### Misleading Folder Names
- **omega_kg_temp/** contains**: Main source code, tests, docs, chrome-extension (not just temp files)
- **Omega_KG_stable/** contains**: Production version with enhanced modules (linear_client, obsidian_sync)
- **Omega_KG_dev/** contains**: Development environment (ephemeral data)

### Hidden Documentation Locations
- **docs/ directory**: Contains comprehensive guides (CONFIGURATION.md, TESTING_SETUP.md, PORT_MAPPING.md)
- **docs/20251130/** subdirectory**: Recent implementation and testing documentation
- **Provider examples**: In src/api/providers/ are canonical reference (docs are outdated)

### Important Context Not Evident from File Structure
- **UI runs in VSCode webview**: Has restrictions (no localStorage, limited APIs)
- **Two separate i18n systems**: Locales in root for extension, webview-ui/src/i18n for UI
- **Monorepo circular dependency**: Packages have circular dependency on types package (intentional)

### Configuration Gotchas
- **OMEGA_ENV marker**: Must be correct in all .env files to prevent data corruption
- **Vault paths differ**: Dev/temp use ./vault (local), stable uses D:/projects/omegavault.as (external)
- **Port mapping**: Different ports per environment (Neo4j: 7687 stable, 7688 dev, 7689 temp)

## Mirmir Protocol & memOS MCP Server Integration (Mandatory)

### Ask Mode Specific Retrieval

BEFORE answering questions, query memOS MCP for relevant context:

```python
# Retrieve architectural decisions
retrieve_context(
    query="multi-environment architecture vault isolation patterns",
    limit=5,
    threshold=0.7
)

# Retrieve code patterns and conventions
retrieve_context(
    query="Neo4j context manager patterns async operations",
    limit=5,
    threshold=0.6
)

# Retrieve historical decisions and their rationale
get_concepts(
    concept_id="architectural-decisions",
    depth=2
)
```

### Recording Documentation Insights

When discovering documentation or explaining complex patterns:

```python
# Record documentation discoveries
mark_significant(
    session_id="ask-session",
    content="Discovered that omega_kg_temp contains main source code, not temp files - counterintuitive naming",
    significance=0.7,
    reason="Prevents confusion when navigating codebase"
)

# Record explanation patterns
scratch_write(
    session_id="ask-session",
    content="Explanation pattern: Multi-env architecture requires explaining vault isolation and port mapping",
    metadata={"pattern": True, "topic": "architecture"}
)

# Promote after comprehensive answers
promote_memory(session_id="ask-session", memory_id="pending-id")
```

**Required recording triggers in Ask Mode:**
- When discovering hidden documentation locations
- When explaining counterintuitive organization
- When clarifying configuration gotchas
- When providing architectural context
- After answering complex questions that reveal new patterns

### Knowledge Cache for Documentation
- **Code organization patterns**: Document counterintuitive structures
- **Configuration requirements**: Track environment-specific settings
- **Architectural decisions**: Record rationale for non-obvious choices
- **Historical context**: Preserve decision-making reasoning