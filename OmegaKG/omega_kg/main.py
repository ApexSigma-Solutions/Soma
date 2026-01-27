import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase, basic_auth
from sqlalchemy import text

from omega_kg.routers import linear_receiver, github_receiver
from omega_kg.routers import guardian
from omega_kg.settings import settings
from omega_kg.database.session import get_db

# from omega_kg.workers.event_processor import EventProcessor
from omega_kg.intelligence import Codex, Mirmir
from omega_kg.routers import terminal, telemetry, capture

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Soma.Brain")

# --- CONFIGURATION ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
HOST_PORT = int(os.getenv("PORT", 8765))


# Global instances
# event_processor = EventProcessor()
codex: Codex = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with Hippocampus (Neo4j), EventProcessor, and Intelligence Layer.

    Startup:
        - Connect to Hippocampus (Neo4j) with retry
        - Initialize Codex for constraint governance
        - Initialize EventProcessor
        - Create background task for polling loop

    Shutdown:
        - Stop EventProcessor gracefully
        - Close Codex connection
        - Disconnect from Hippocampus
        - Wait for task completion with timeout
    """
    global codex

    try:
        # 1. Connect to Hippocampus (Neo4j) with retry
        max_retries = 5
        for attempt in range(max_retries):
            try:
                app.state.neo4j_driver = GraphDatabase.driver(
                    NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
                )
                app.state.neo4j_driver.verify_connectivity()
                logger.info("Hippocampus (Neo4j) Connected.")
                break
            except Exception as e:
                wait = 2**attempt
                logger.error(
                    f"Hippocampus Connection Failed: {e}. Retrying in {wait}s..."
                )
                time.sleep(wait)
        else:
            logger.critical(
                "Hippocampus Unreachable. Brain operating in detached mode."
            )
            # Do NOT raise error, allow app to start so we can debug via /health
            app.state.neo4j_driver = None

        # 2. Initialize Codex (Intelligence Layer)
        logger.info("Application startup: Initializing Codex")
        try:
            codex = Codex()
            codex.connect()
            logger.info("[OK] Codex initialized and connected")
        except Exception as e:
            logger.warning(
                f"Failed to initialize Codex: {e}. Intelligence layer will be unavailable."
            )
            codex = None

        # 3. Initialize EventProcessor
        logger.info("Application startup: EventProcessor migrated to InGest (Skipped)")
        # processor_task = asyncio.create_task(event_processor.start())
        processor_task = None

        yield  # Application runs here

    except Exception as e:
        logger.critical(f"FATAL STARTUP ERROR: {e}", exc_info=True)
        raise e

    finally:
        # Shutdown
        # logger.info("Application shutdown: Stopping EventProcessor")
        # await event_processor.stop()

        # Wait for task to complete (with timeout)
        if processor_task:
            try:
                await asyncio.wait_for(processor_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("EventProcessor did not stop gracefully, cancelling")
                processor_task.cancel()

        # Close Codex connection
        if codex:
            codex.close()
            logger.info("[OK] Codex connection closed")

        # Disconnect from Hippocampus
        if hasattr(app.state, "neo4j_driver") and app.state.neo4j_driver:
            app.state.neo4j_driver.close()
            logger.info("Hippocampus Disconnected.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- CORS Configuration for Hybrid Architecture (Tailscale Support) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*",
        "http://sigma-desktop:*",  # Tailscale hostname
    ],
    allow_origin_regex=r"http://100\..*",  # Tailscale IP range (100.x.x.x)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# API v1 - Versioned Interservice Contracts
# =============================================================================
# All interservice endpoints are versioned under /v1 to ensure backward
# compatibility as the Soma ecosystem evolves.

v1_router = APIRouter(prefix="/v1", tags=["v1"])

# Guardian (Immune System) - /v1/guardian/*
v1_router.include_router(guardian.router)

# Webhook Receivers - /v1/webhooks/*
v1_router.include_router(linear_receiver.router, tags=["Linear Ingest"])
v1_router.include_router(github_receiver.router, tags=["GitHub Ingest"])


# Terminal Capture - /v1/capture/terminal
v1_router.include_router(terminal.router)

# Capture Router - /v1/capture/* (includes /auth/token)
v1_router.include_router(capture.router)

# Telemetry - /v1/telemetry/*
v1_router.include_router(telemetry.router)

# MCP router for intelligence layer tools - /v1/mcp/*
mcp_router = APIRouter(prefix="/mcp", tags=["MCP"])


@mcp_router.post("/tools/consult_codex")
async def consult_codex(action_description: str) -> dict[str, Any]:
    """
    Consult the Codex before implementing complex features.

    Agents must call this before implementing features to check for known prohibitions.

    Args:
        action_description: Description of proposed action

    Returns:
        Mirmir verdict with approval status and details
    """
    if not codex:
        return {
            "error": "Codex not initialized",
            "message": "Intelligence layer unavailable",
        }

    mirmir = Mirmir(codex)
    verdict = mirmir.review_action(action_description)

    return {
        "allowed": verdict.approved,
        "reason": verdict.message,
        "constraint_id": verdict.violations[0] if verdict.violations else None,
        "verdict": verdict.dict(),
    }


v1_router.include_router(mcp_router)

# Mount v1 API
app.include_router(v1_router)


@app.get("/health")
async def health_check():
    """
    Validates App and DB Health
    """
    db_status = "disconnected"
    try:
        # Probe DB
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            db_status = "connected"
            break  # Only need one
    except Exception as e:
        db_status = f"error: {str(e)}"

    codex_status = "unavailable"
    if codex and codex.is_connected():
        codex_status = "connected"

    return {
        "status": "online",
        "version": settings.VERSION,
        "database": db_status,
        "event_processor": "migrated_to_ingest",
        "codex": codex_status,
    }


# --- EXECUTION ENTRY POINT ---
if __name__ == "__main__":
    # This runs when Docker calls 'python -m omega_kg.main'
    uvicorn.run(
        "omega_kg.main:app",
        host="0.0.0.0",
        port=HOST_PORT,
        reload=False,  # Reload False in Docker to prevent signal issues
    )
