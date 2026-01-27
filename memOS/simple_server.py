#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple memOS.MCP Server Runner
Direct execution of the server without complex middleware
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import and run the server
if __name__ == "__main__":
    # Import the server module
    from memos_mcp.server import mcp_server

    print("🚀 Starting memOS.MCP Server in stdio mode...")
    try:
        mcp_server.run()
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
