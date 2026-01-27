#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct memOS.MCP Server Runner
Direct execution of the server without tool registration
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import and run the server
if __name__ == "__main__":
    # Import the server module directly
    from fastmcp import FastMCP
    from contextlib import asynccontextmanager
    from memos_mcp.config import Settings
    from memos_mcp.logic import MemosLogic

    # Global Logic Instance
    logic_instance = None

    @asynccontextmanager
    async def lifespan(server):
        """
        Manages the lifecycle of the memOS server.
        Initializes database connections on startup.
        """
        global logic_instance
        print("🚀 Starting memOS MCP Server (Port 8768)...")

        settings = Settings()

        try:
            # Initialize Core Logic (Database, Vector Store, etc.)
            logic_instance = MemosLogic(settings)
            await logic_instance.initialize()
            print("✅ memOS Logic Layer Initialized.")

            yield

        except Exception as e:
            print(f"❌ Critical Startup Failure: {e}")
            raise
        finally:
            print("🛑 Shutting down memOS MCP Server...")
            if logic_instance:
                await logic_instance.shutdown()

    # Initialize FastMCP
    mcp_server = FastMCP("memOS", lifespan=lifespan)

    print("Starting memOS.MCP Server...")
    try:
        # Run the server directly without tool registration
        mcp_server.run()
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)
