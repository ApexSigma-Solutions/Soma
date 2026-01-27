"""
memOS MCP Server Package Main Entrypoint
Allows running the server with `python -m memos_mcp`
"""

from memos_mcp.server import mcp_server

if __name__ == "__main__":
    mcp_server.run()
