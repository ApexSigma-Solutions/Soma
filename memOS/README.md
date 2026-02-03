# Hands: memOS (Interaction)

## Overview
memOS (formerly memos.MCP) is the motor control layer of the Soma organism. It provides a FastMCP 2.0 interface for agents to retrieve context from the Brain and promote working memories into the long-term Codex.

## Role in Soma
- **Function**: agentic_interface
- **Port**: 8768
- **Brain Connection**: Neo4j (Read-only for retrieval, Write via promote_memory).
- **Memory Tiers**:
  - **Tier 1 (Working)**: Redis-backed ephemeral memory.
  - **Tier 2 (Brain)**: Neo4j/Vector-backed retrieval.

## MCP Server Configuration

memOS is configured as a Model Context Protocol (MCP) server using FastMCP 2.0.

### Available Tools

| Category | Tool | Description |
|----------|------|-------------|
| **Scratchpad** | `read_scratchpad` | Read session notes |
| | `write_scratchpad` | Add quick notes |
| | `clear_scratchpad` | Clear session notes |
| **Context** | `retrieve_context` | Hybrid search WM + LTM |
| | `get_concepts` | Extract key concepts |
| | `get_constraints` | Get system constraints |
| **Intelligence** | `consult_mirmir` | AI plan validation |
| | `verify_implementation` | Verify against constraints |
| **Promotion** | `mark_significant` | Mark memory importance |
| | `promote_memory` | Promote WM to LTM |

### Quick Start

```bash
# Install dependencies
cd memOS
poetry install

# Run MCP server
poetry run python -m memos_mcp.server
```

### Claude Desktop Integration

Add to `%APPDATA%/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memos": {
      "command": "python",
      "args": ["-m", "memos_mcp.server"],
      "cwd": "D:/projects/Soma/memOS",
      "env": {
        "MEMOS_API_KEY": "sigma-dev-secret-key",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password",
        "REDIS_URL": "redis://localhost:6380",
        "OMEGAKG_URL": "http://localhost:8765"
      }
    }
  }
}
```

### Environment Variables

```env
MEMOS_API_KEY=sigma-dev-secret-key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
REDIS_URL=redis://localhost:6380
POSTGRES_URL=postgresql://postgres:postgres@localhost:6000/soma
OMEGAKG_URL=http://localhost:8765
```

## Operational Control
- **Executive**: Managed via [orchestrator.py](../orchestrator.py) or [start_ecosystem.ps1](../start_ecosystem.ps1).
- **Verification**: Confirm tool availability via MCP client or Cortex dashboard.

## Documentation
- [Soma Root AGENTS.md](../AGENTS.md)
- [Soma Root README.md](../README.md)
- [memOS MCP Guide](../.claude/mcp/MEMOS_MCP_GUIDE.md)
- [memOS Setup Guide](./docs/configuration.md)
