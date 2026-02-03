# memOS MCP Server Configuration

## Overview

memOS is configured as a FastMCP (Model Context Protocol) server, providing AI agents with access to working memory, context retrieval, and memory promotion capabilities.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude/AI     │────▶│   memOS MCP      │────▶│   Redis (WM)    │
│   Agent         │     │   Server (8768)  │     ├─────────────────┤
└─────────────────┘     └──────────────────┘     │   Neo4j (LTM)   │
         │                      │                 ├─────────────────┤
         │                      ▼                 │   OmegaKG API   │
         │               ┌──────────────────┐     └─────────────────┘
         │               │   Tool Registry  │
         │               │   - scratchpad   │
         │               │   - context      │
         │               │   - mirmir       │
         │               │   - promote      │
         │               └──────────────────┘
         │
         └──────────────────────────────────────────────┐
                                                          ▼
                                               ┌──────────────────┐
                                               │   Response       │
                                               │   - Working Mem  │
                                               │   - Context      │
                                               │   - Suggestions  │
                                               └──────────────────┘
```

## Available Tools

### 1. Scratchpad Tools (`tools/memory.py`)

**Purpose**: Temporary session-based note storage

| Tool | Description |
|------|-------------|
| `read_scratchpad` | Read all entries for a session |
| `write_scratchpad` | Add a new scratchpad entry |
| `clear_scratchpad` | Clear all entries for a session |

**Parameters**:
- `session_id`: Unique session identifier
- `content`: Text content to store
- `metadata`: Optional key-value pairs

### 2. Context Retrieval Tools (`tools/context.py`)

**Purpose**: Retrieve relevant context from working and long-term memory

| Tool | Description |
|------|-------------|
| `retrieve_context` | Hybrid search across WM and LTM |
| `get_concepts` | Extract key concepts from query |
| `get_constraints` | Get system constraints |

**Parameters**:
- `query`: Search query string
- `agent_id`: Agent identifier
- `limit`: Maximum results (default: 10)
- `threshold`: Relevance threshold (default: 0.7)

### 3. Intelligence Tools (`tools/intelligence.py`)

**Purpose**: AI-powered plan validation and recommendations

| Tool | Description |
|------|-------------|
| `consult_mirmir` | Validate implementation plan |
| `verify_implementation` | Verify code against constraints |

**Parameters**:
- `plan`: Implementation plan text
- `context`: Additional context

### 4. Memory Promotion Tools (`tools/memory.py`)

**Purpose**: Promote working memory to long-term storage

| Tool | Description |
|------|-------------|
| `mark_significant` | Mark memory as significant |
| `promote_memory` | Promote to long-term memory |

**Parameters**:
- `session_id`: Session identifier
- `key`: Memory key to promote
- `significance`: low/medium/high

## Configuration

### Environment Variables

Create `.env` file in `memOS/` directory:

```env
# API Security
MEMOS_API_KEY=sigma-dev-secret-key

# Neo4j (Long-term Memory)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Redis (Working Memory)
REDIS_URL=redis://localhost:6380

# PostgreSQL
POSTGRES_URL=postgresql://postgres:postgres@localhost:6000/soma

# OmegaKG API
OMEGAKG_URL=http://localhost:8765

# Observability (Optional)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=
```

### Claude Desktop Integration

Add to Claude Desktop config (`%APPDATA%/Claude/claude_desktop_config.json` on Windows):

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
        "POSTGRES_URL": "postgresql://postgres:postgres@localhost:6000/soma",
        "OMEGAKG_URL": "http://localhost:8765"
      }
    }
  }
}
```

## Running the MCP Server

### Development Mode

```powershell
cd memOS
poetry install
poetry run python -m memos_mcp.server
```

### Production Mode

```powershell
cd memOS
poetry install --only main
poetry run python -m memos_mcp.server
```

### Docker Mode

```powershell
docker-compose up memos
```

## Testing MCP Tools

### Using Claude Desktop

1. Start the memOS MCP server
2. Open Claude Desktop
3. Ask Claude to use memOS tools:
   - "Read my scratchpad for session dev-001"
   - "Retrieve context about authentication"
   - "Consult Mirmir about my implementation plan"

### Using MCP Inspector

```powershell
npx @anthropics/mcp-inspector
# Connect to memos server and test tools
```

## API Endpoints (HTTP Mode)

When running with HTTP transport:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/v1/tools/list` | GET | List available tools |
| `/mcp/v1/tools/call` | POST | Call a tool |
| `/health` | GET | Health check |

## Integration with Cortex Dashboard

The Cortex dashboard provides UI components for all memOS capabilities:

- **ScratchpadInterface**: Session-based note taking
- **WorkingMemoryViewer**: Real-time WM display
- **MemoryPromotionInterface**: Promote to LTM
- **MirmirConsultationUI**: AI plan validation
- **ContextRetrievalSearch**: Hybrid search UI

## Troubleshooting

### Connection Issues

1. Verify all services are running:
   ```powershell
   python scripts/health_check.py
   ```

2. Check Neo4j connection:
   ```powershell
   curl http://localhost:7474
   ```

3. Check Redis connection:
   ```powershell
   redis-cli -p 6380 ping
   ```

### Tool Call Failures

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

- Increase Redis connection pool size
- Enable Neo4j query caching
- Use connection pooling for PostgreSQL

## Security Considerations

1. **API Key**: Always set `MEMOS_API_KEY` in production
2. **Network**: Use Tailscale or VPN for remote access
3. **Secrets**: Store passwords in Bitwarden or similar
4. **Logging**: Disable debug logging in production

## Development

### Adding New Tools

1. Create tool in `src/memos_mcp/tools/`:
   ```python
   from fastmcp import mcp

   @mcp.tool()
   async def my_new_tool(param: str) -> dict:
       """Tool description"""
       return {"result": "success"}
   ```

2. Import in `server.py`:
   ```python
   from .tools import my_new_tool
   ```

3. Test with MCP Inspector

4. Update this documentation

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Spec](https://modelcontextprotocol.io/)
- [memOS README](../memOS/README.md)
- [Soma Architecture](../docs/SYSTEM_ARCHITECTURE_SUMMARY.md)
