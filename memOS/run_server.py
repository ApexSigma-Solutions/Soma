#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple memOS.MCP Server Runner
Direct execution of the server without middleware complications
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import and run the server
if __name__ == "__main__":
    # Import the server module
    from memos_mcp.server import mcp_server

    # Check if --sse flag is passed
    if "--sse" in sys.argv:
        print("🚀 Starting memOS.MCP Server in SSE mode on Port 8768...")
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

            # Add CORS middleware for Cortex Dashboard & Chrome Extension
            from fastapi.middleware.cors import CORSMiddleware

            wrapper_app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Dev mode - allow all origins
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            # Add Health Check
            @wrapper_app.get("/health")
            async def health_check():
                return {"status": "healthy", "service": "memOS.MCP"}

            # Add Memory Storage Endpoint (Bridge for InGest-LLM)
            from pydantic import BaseModel, Field
            from enum import Enum
            from typing import Optional, List, Dict, Any

            class MemoryTier(str, Enum):
                WORKING = "working"
                EPISODIC = "episodic"
                SEMANTIC = "semantic"
                PROCEDURAL = "procedural"

            class MemoryStorageRequest(BaseModel):
                content: str
                memory_tier: MemoryTier
                metadata: Dict[str, Any] = Field(default_factory=dict)
                embedding: Optional[List[float]] = None
                relationships: Optional[List[Dict[str, Any]]] = None

            @wrapper_app.post("/memory/{tier}/store")
            async def store_memory_endpoint(tier: str, request: MemoryStorageRequest):
                """
                Handle memory storage requests from InGest-LLM.
                """
                global logic_instance
                if not logic_instance:
                    return {"status": "error", "message": "Logic layer not initialized"}

                print(
                    f"📥 Received storage request for tier {tier}: {request.memory_tier}"
                )

                try:
                    # Use logic_instance to store
                    result = await logic_instance.store(
                        content=request.content, metadata=request.metadata
                    )

                    # Parse the result string (logic.store returns string)
                    if result.startswith("Memory stored successfully"):
                        import re

                        match = re.search(r"ID: ([a-f0-9\-]+)", result)
                        mem_id = match.group(1) if match else "unknown"
                        return {"status": "success", "memory_id": mem_id, "tier": tier}
                    else:
                        return {"status": "error", "message": result}

                except Exception as e:
                    print(f"Storage endpoint error: {e}")
                    return {"status": "error", "message": str(e)}

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
        print("🚀 Starting memOS.MCP Server in stdio mode...")
        mcp_server.run()
