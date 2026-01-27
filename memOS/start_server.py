#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memOS.MCP Server Startup Script
Ensures proper encoding and path handling
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import and run the server
if __name__ == "__main__":
    # Check if --sse flag is passed
    if "--sse" in sys.argv:
        # Import the server module
        from memos_mcp.server import mcp_server

        # Run in SSE mode
        try:
            # Get the Starlette app from FastMCP
            request_app = mcp_server.sse_app()

            # Create a wrapper FastAPI app
            from fastapi import FastAPI
            from contextlib import asynccontextmanager
            from memos_mcp.config import Settings
            from memos_mcp.logic import MemosLogic

            # Global Logic Instance
            logic_instance = None

            @asynccontextmanager
            async def wrapper_lifespan(app: FastAPI):
                global logic_instance
                print("🚀 Initializing Logic Layer via Wrapper Lifespan...")
                settings = Settings()
                try:
                    logic_instance = MemosLogic(settings)
                    await logic_instance.initialize()
                    print("✅ memOS Logic Layer Initialized.")
                    yield
                finally:
                    print("🛑 Shutting down Logic Layer...")
                    if logic_instance:
                        await logic_instance.shutdown()

            wrapper_app = FastAPI(lifespan=wrapper_lifespan)

            # Add CORS Middleware
            from fastapi.middleware.cors import CORSMiddleware

            wrapper_app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            # Add Health Check
            @wrapper_app.get("/health")
            async def health_check():
                return {"status": "healthy", "service": "memOS.MCP"}

            # Mount the SSE app
            wrapper_app.mount("/", request_app)

            # Run with Uvicorn
            import uvicorn

            uvicorn.run(wrapper_app, host="0.0.0.0", port=8768)

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            sys.exit(1)
    else:
        # Run stdio server (default for Claude Desktop and local MCP clients)
        from memos_mcp.server import mcp_server

        mcp_server.run()
