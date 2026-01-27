# MCP Configuration for OmegaKG

## Overview
Configured Claude Code to use Model Context Protocol (MCP) servers via `.mcp.json` in workspace root.

## Configured Servers

### 1. memOS.MCP
**Location**: `memos.MCP/` directory
**Type**: stdio
**Command**: `poetry run python -m memos_mcp`
**Port**: N/A (stdio communication)

**Available Tools**:
- Intelligence Layer: `consult_mirmir`, `verify_implementation`
- Context Retrieval: `retrieve_context`, `get_concepts`, `get_constraints`
- Working Memory: `scratch_write`, `scratch_read`, `scratch_clear`, `set_working_memory`, `get_working_memory`
- Learning: `mark_significant`, `promote_memory`

**Prerequisites**:
- Redis (port 6379)
- PostgreSQL with pgvector (port 5800)
- Neo4j (port 7687)
- Ollama (port 11434)

**Environment Variables Required**:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `NEO4J_PASSWORD`

### 2. Serena
**Type**: stdio
**Command**: `poetry run mcp-server-oraios-serena`
**Purpose**: Semantic code navigation and manipulation

## Configuration Files Created

1. **`.mcp.json`** - Main MCP configuration in workspace root
2. **`docs/MCP_CONFIGURATION.md`** - Comprehensive setup guide
3. **`docs/MCP_QUICK_REFERENCE.md`** - Quick reference for tool usage

## Usage Pattern

### Mirmir Protocol Workflow
1. Agent describes intended high-risk change
2. Claude Code calls `consult_mirmir()` automatically
3. Returns verdict with approval/rejection and risk score
4. If approved, agent proceeds with implementation
5. Claude Code calls `verify_implementation()` to validate result

### Context Retrieval Workflow
1. Agent asks about architecture/patterns
2. Claude Code calls `retrieve_context()` or `get_concepts()`
3. Receives semantic search results or graph traversal
4. Provides informed response with citations

### Working Memory Workflow
1. Agent uses `scratch_write()` to trace reasoning
2. Stores intermediate results via `set_working_memory()`
3. Retrieves context as needed via `get_working_memory()`
4. Marks significant discoveries via `mark_significant()`
5. Promotes valuable insights via `promote_memory()`

## Activation

1. Claude Code auto-detects `.mcp.json`
2. Prompts for approval on first use (security)
3. Tools become available in conversation
4. Ask "What MCP tools are available?" to verify

## Troubleshooting

**Server won't start**: Check prerequisites are running
**Tools not appearing**: Reload window, check JSON syntax
**Permission errors**: Click "Allow" when Claude Code prompts

## Integration with Ecosystem

- **memOS.MCP** → **InGest-LLM.as** → **PostgreSQL/Neo4j** (persistent storage)
- **Mirmir Protocol** enforces architectural constraints from Codex
- **Working Memory** uses Redis for ephemeral storage
- **Vector Search** uses pgvector for semantic retrieval
- **Graph Queries** use Neo4j for relationship traversal

## Security

- Credentials via system environment variables
- Claude Code prompts before executing tools
- Mirmir Protocol acts as safety net for dangerous operations
- Audit trail for all constraint consultations

## References

- MCP Specification: https://github.com/modelcontextprotocol
- Claude Code Docs: https://code.claude.com/docs/en/mcp
- memOS.MCP AGENTS.md: memos.MCP/AGENTS.md
- Workspace AGENTS.md: AGENTS.md (Mirmir Protocol section)
