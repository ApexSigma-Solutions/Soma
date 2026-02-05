"""
memOS MCP Server Entrypoint
Integrates local tools and the Omega Intelligence Layer.
"""

import sys
import os

# Force UTF-8 for stdout/stderr on Windows to prevent logging crashes
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


from fastmcp import FastMCP

# Import Configuration
from memos_mcp.config import Settings

# Import Core Logic
from memos_mcp.logic import MemosLogic

# Import Tools (The Mirmir Bridge)
# Import Tools
from memos_mcp.tools.intelligence import consult_mirmir, verify_implementation
from memos_mcp.tools.context import retrieve_context, get_concepts, get_constraints
from memos_mcp.tools.memory import (
    scratch_write,
    scratch_read,
    scratch_clear,
    set_working_memory,
    get_working_memory,
    mark_significant,
    promote_memory,
)

# Import Soma-specific tools
from memos_mcp.tools.soma_tools import ingest_signal, query_brain, promote_to_codex

# Import Pulse Worker
from memos_mcp.workers import JanitorWorker, ConsolidationThresholds
from memos_mcp.memory import get_redis_client

# Configure Logging
from memos_mcp.observability import configure_logging

# Configure Logging
log_dir = "d:/projects/OmegaKG/logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

configure_logging("memos_mcp", log_dir)
logger = logging.getLogger("memos_mcp")

# Global Logic Instance
logic_instance: MemosLogic = None
# Global Janitor Worker
janitor_worker: Optional[JanitorWorker] = None


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


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    """
    Manages the lifecycle of the memOS server.
    Initializes database connections on startup.
    """
    global logic_instance
    logger.info("🚀 Starting memOS MCP Server (Port 8768)...")

    settings = Settings()

    try:
        # Initialize Core Logic (Database, Vector Store, etc.)
        logic_instance = MemosLogic(settings)
        await logic_instance.initialize()
        logger.info("✅ memOS Logic Layer Initialized.")

        yield

    except Exception as e:
        logger.error(f"❌ Critical Startup Failure: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down memOS MCP Server...")
        if logic_instance:
            await logic_instance.shutdown()


# Initialize FastMCP
mcp_server = FastMCP("memOS", lifespan=lifespan)

# Export app for uvicorn compatibility
# Export app for uvicorn compatibility
app = mcp_server

# --- CORS Middleware ---
# Note: FastMCP doesn't support add_middleware directly.
# CORS is handled in the SSE wrapper app instead.

# --- REGISTER TOOLS ---

# 1. Intelligence Layer (The Brain)
mcp_server.add_tool(consult_mirmir)
mcp_server.add_tool(verify_implementation)

# 2. Context Retrieval (Queries)
mcp_server.add_tool(retrieve_context)
mcp_server.add_tool(get_concepts)
mcp_server.add_tool(get_constraints)

# 3. Working Memory (Hands)
mcp_server.add_tool(scratch_write)
mcp_server.add_tool(scratch_read)
mcp_server.add_tool(scratch_clear)
mcp_server.add_tool(set_working_memory)
mcp_server.add_tool(get_working_memory)

# 4. Learning (Hands -> Brain)
mcp_server.add_tool(mark_significant)
mcp_server.add_tool(promote_memory)

# 5. Soma Integration (Organism Interfaces)
mcp_server.add_tool(ingest_signal)  # -> InGress (The Senses)
mcp_server.add_tool(query_brain)  # <- Neo4j (The Brain, read-only)
mcp_server.add_tool(promote_to_codex)  # -> OmegaKG -> Codex (via Guardian)


@mcp_server.resource("config://status")
def get_system_status() -> str:
    """Returns the health status of the memOS ecosystem."""
    status = "ONLINE" if logic_instance else "INITIALIZING"
    return f"memOS Status: {status}\nIntelligence Layer: ACTIVE (Mirmir Connected)"


# HTTP Endpoints removed as FastMCP does not support arbitrary HTTP routes directly.
# Use MCP tools instead.

if __name__ == "__main__":
    import sys
    import subprocess
    from pathlib import Path
    import uvicorn
    from fastapi import FastAPI

    # Run Documentation Enforcement (The Immune System)
    try:
        # Locate script relative to this file
        current_dir = Path(__file__).resolve().parent
        script_path = (
            current_dir.parent.parent / "scripts" / "maintenance" / "enforce_docs.py"
        )

        if script_path.exists():
            logger.info("🛡️ Running Mimir Documentation Enforcement...")
            # Use same python executable
            subprocess.run(
                [sys.executable, str(script_path)], check=True, capture_output=True
            )
            logger.info("✅ Mimir Documentation Verified.")
        else:
            logger.warning(f"⚠️ Docs script not found at {script_path}")

    except Exception as e:
        logger.error(f"⚠️ Documentation enforcement failed (Soft Fail): {e}")

    # Check for SSE mode flag
    if "--sse" in sys.argv:
        logger.info("Starting in SSE mode with Health Check...")

        # 1. Get the Starlette app from FastMCP
        request_app = mcp_server.sse_app()

        # 2. Create a wrapper FastAPI app
        @asynccontextmanager
        async def wrapper_lifespan(app: FastAPI):
            global logic_instance, janitor_worker
            logger.info("🚀 Initializing Logic Layer via Wrapper Lifespan...")
            settings = Settings()
            try:
                logic_instance = MemosLogic(settings)
                await logic_instance.initialize()
                logger.info("✅ memOS Logic Layer Initialized.")

                # Start Janitor worker if enabled
                if settings.janitor_enabled:
                    janitor_worker = JanitorWorker(
                        stream_key=settings.janitor_stream_key,
                        thresholds=ConsolidationThresholds(
                            buffer_size=settings.janitor_buffer_size,
                            timeout_seconds=settings.janitor_timeout_seconds,
                        ),
                        omegakg_url=settings.omegakg_validate_url,
                    )
                    await janitor_worker.start()
                    logger.info("✅ Janitor worker started")

                yield
            finally:
                logger.info("🛑 Shutting down Logic Layer...")

                # Stop Janitor worker
                if janitor_worker:
                    await janitor_worker.stop()

                if logic_instance:
                    await logic_instance.shutdown()

        wrapper_app = FastAPI(lifespan=wrapper_lifespan)

        # 3. Add CORS Middleware (Required for Dashboard)
        from fastapi.middleware.cors import CORSMiddleware

        wrapper_app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:5173",  # Cortex dev (legacy)
                "http://localhost:6001",  # Cortex (current)
                "http://127.0.0.1:6001",  # Cortex (IP)
                "http://localhost:3000",  # Alternative dev
            ],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

        # 4. Add Health Check (Required for Dashboard)
        @wrapper_app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "memOS.MCP"}

        # 6. Add Memory Storage Endpoint (Bridge for InGest-LLM)
        # Defined BEFORE mounting request_app to avoid shadowing by root mount
        @wrapper_app.post("/memory/{tier}/store")
        async def store_memory_endpoint(tier: str, request: MemoryStorageRequest):
            """
            Handle memory storage requests from InGest-LLM.
            """
            global logic_instance
            if not logic_instance:
                return {"status": "error", "message": "Logic layer not initialized"}

            logger.info(
                f"📥 Received storage request for tier {tier}: {request.memory_tier}"
            )

            # Map numeric tiers if necessary (InGest-LLM might send "3" in URL)
            # Logic currently supports generic storage via pgvector.
            # Ideally we route to Neo4j for tier 3, but pgvector is the fallback.

            try:
                # Use logic_instance to store
                # We pass the full metadata from the request
                result = await logic_instance.store(
                    content=request.content, metadata=request.metadata
                )

                # Parse the result string (logic.store returns string)
                # logic.store returns: "Memory stored successfully (ID: ...)" or "Store failed: ..."
                if result.startswith("Memory stored successfully"):
                    import re

                    match = re.search(r"ID: ([a-f0-9\-]+)", result)
                    mem_id = match.group(1) if match else "unknown"
                    return {"status": "success", "memory_id": mem_id, "tier": tier}
                else:
                    return {"status": "error", "message": result}

            except Exception as e:
                logger.error(f"Storage endpoint error: {e}")
                return {"status": "error", "message": str(e)}

        # 10. Add Mirmir Consult Endpoint (Bridge for Dashboard)
        class MirmirConsultRequest(BaseModel):
            query: str
            intended_outcome: str = "Query via Dashboard"

        @wrapper_app.post("/mirmir/consult")
        async def consult_mirmir_endpoint(request: MirmirConsultRequest):
            """
            Expose consult_mirmir tool via HTTP for the dashboard.
            """
            try:
                # Pass query as plan_text
                result = await consult_mirmir(
                    plan_text=request.query, intended_outcome=request.intended_outcome
                )
                # MirmirVerdict is a Pydantic model, so we can return it dict()
                return {"status": "success", "result": result.dict()}
            except Exception as e:
                logger.error(f"Mimir consult failed: {e}")
                return {"status": "error", "message": str(e)}

        # 7. Add Pulse Event Emission Endpoint
        class PulseEmitRequest(BaseModel):
            event_type: str
            payload: Dict[str, Any]
            session_id: Optional[str] = None

        @wrapper_app.post("/pulse/emit")
        async def emit_pulse_event(request: PulseEmitRequest):
            """
            Emit a pulse event to the stream.

            Events are captured for real-time monitoring and automatic consolidation.
            """
            try:
                redis_client = get_redis_client()
                stream_id = await redis_client.emit_pulse_event(
                    event_type=request.event_type,
                    payload=request.payload,
                    session_id=request.session_id,
                )
                return {"status": "ok", "stream_id": stream_id}
            except Exception as e:
                logger.error(f"Failed to emit pulse event: {e}")
                return {"status": "error", "message": str(e)}

        # 8. Add Pulse Stream SSE Endpoint (for Dashboard)
        from sse_starlette.sse import EventSourceResponse

        @wrapper_app.get("/pulse/stream")
        async def pulse_stream_sse():
            """
            Stream pulse events to dashboard via Server-Sent Events.
            """

            async def event_generator():
                redis_client = get_redis_client()
                await redis_client.connect()
                last_id = "$"  # Start from new events only

                try:
                    while True:
                        # Read from stream with 5 second timeout
                        events = await redis_client.read_pulse_stream(
                            last_id=last_id,
                            count=10,
                            block_ms=5000,
                        )

                        if events:
                            for event in events:
                                # Format as SSE
                                yield {
                                    "event": "pulse",
                                    "data": event.model_dump_json(),
                                }
                                last_id = event.event_id
                        else:
                            # Send keepalive
                            yield {"event": "ping", "data": ""}

                except Exception as e:
                    logger.error(f"SSE stream error: {e}")
                    yield {"event": "error", "data": str(e)}

            return EventSourceResponse(event_generator())

        # 9. Add Stats Endpoint (for Dashboard memOS metrics)
        @wrapper_app.get("/stats")
        async def get_memory_stats():
            """
            Return memory statistics for dashboard.
            Exposes PGVectorStore.get_stats() via HTTP.
            """
            from memos_mcp.database import get_pgvector_store

            store = get_pgvector_store()
            try:
                stats = await store.get_stats()
                return {
                    "total_memories": stats.get("total_memories", 0),
                    "by_agent": stats.get("memories_by_agent", {}),
                    "by_tier": {
                        "semantic": stats.get("total_memories", 0),
                        "procedural": 0,  # Not tracked separately yet
                    },
                    "vector_dimension": 1024,
                }
            except Exception as e:
                logger.error(f"Failed to get stats: {e}")
                return {
                    "total_memories": 0,
                    "by_agent": {},
                    "by_tier": {"semantic": 0, "procedural": 0},
                    "vector_dimension": 1024,
                    "error": str(e),
                }

        # 5. Mount the SSE app
        # We mount at root so /sse and /messages work as expected
        wrapper_app.mount("/", request_app)

        # 6. Run with Uvicorn
        uvicorn.run(wrapper_app, host="0.0.0.0", port=8768)

    else:
        # Start stdio server (default for Claude Desktop and local MCP clients)
        mcp_server.run()
