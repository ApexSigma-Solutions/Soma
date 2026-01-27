# memOS.MCP Client Configuration

This guide provides configuration snippets to connect various agents and IDEs to the memOS.MCP server.

## 📋 Prerequisites

Ensure you have the absolute path to your environment correctly configured.
**Project Root:** `D:\projects\OmegaKG\memos.MCP`
**Python Venv:** `D:\projects\OmegaKG\memos.MCP\.venv`
**FastMCP Binary:** `D:\projects\OmegaKG\memos.MCP\.venv\Scripts\fastmcp.exe`
**Server Script:** `src\memos_mcp\server.py`

---

## 🖥️ Claude Desktop

Add this to your `claude_desktop_config.json`:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "memOS": {
      "command": "D:\\projects\\OmegaKG\\memos.MCP\\.venv\\Scripts\\fastmcp.exe",
      "args": [
        "run",
        "src\\memos_mcp\\server.py"
      ],
      "cwd": "D:\\projects\\OmegaKG\\memos.MCP",
      "env": {
        "PYTHONPATH": "src",
        "POSTGRES_PASSWORD": "omega_dev_password"
      }
    }
  }
}
```

---

## 🖱️ Cursor

1. Open **Cursor Settings** > **Features** > **MCP**.
2. Click **+ Add New Internal Server**.
3. Fill in the details:
   - **Name:** `memOS`
   - **Type:** `stdio`
   - **Command:** `D:\projects\OmegaKG\memos.MCP\.venv\Scripts\fastmcp.exe run src\memos_mcp\server.py`
   - **Environment Variables:** (Add as needed, e.g. `POSTGRES_PASSWORD` if not in .env)

---

## 🆚 VS Code (Generic MCP Extension)

If using an MCP extension in VS Code, typical configuration matches the JSON format:

```json
{
  "mcp.servers": {
    "memOS": {
      "command": "D:\\projects\\OmegaKG\\memos.MCP\\.venv\\Scripts\\fastmcp.exe",
      "args": ["run", "src\\memos_mcp\\server.py"],
      "cwd": "D:\\projects\\OmegaKG\\memos.MCP",
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

---

## 🦘 RooCode / Kilo Code

For tools using standard MCP configuration files (often sharing `claude_desktop_config.json` or similar):

**Command:**
```cmd
D:\projects\OmegaKG\memos.MCP\.venv\Scripts\fastmcp.exe run src\memos_mcp\server.py
```

**Working Directory:**
```
D:\projects\OmegaKG\memos.MCP
```

---

## 🤖 Claude Code (CLI)

Run the server directly as a subcommand or configure via project settings if available. Since Claude Code is often project-scoped:

```bash
# Run momentarily
fastmcp run src/memos_mcp/server.py
```

---

## ♊ Gemini CLI / Other Stdio Clients

Run the server in stdio mode:

```powershell
d:
cd D:\projects\OmegaKG\memos.MCP
.venv\Scripts\fastmcp.exe run src\memos_mcp\server.py
```

The server listens on `stdio` by default.

---

## 🌐 Remote Connections (SSE)

To run the server for remote access (e.g. from a different machine or container):

```powershell
.venv\Scripts\fastmcp.exe run src\memos_mcp\server.py --transport sse --port 8768
```

Connect your client to: `http://localhost:8768/sse`
