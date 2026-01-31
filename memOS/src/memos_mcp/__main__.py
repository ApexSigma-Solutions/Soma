"""
memOS MCP Server Package Main Entrypoint
Allows running the server with `python -m memos_mcp`

By default, runs in SSE mode with HTTP server for Soma integration.
Use `python -m memos_mcp --stdio` for stdio mode (Claude Desktop).
"""

import sys

if __name__ == "__main__":
    # Default to SSE mode for Soma ecosystem
    # The --sse flag triggers HTTP server with health endpoints
    if "--stdio" not in sys.argv and "--sse" not in sys.argv:
        sys.argv.append("--sse")

    # Import and run the server module's main block
    # This triggers the if __name__ == "__main__" logic in server.py
    import runpy

    runpy.run_module("memos_mcp.server", run_name="__main__", alter_sys=True)
