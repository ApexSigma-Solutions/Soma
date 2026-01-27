"""Soma.InGress - The Senses Layer.

A lightweight FastAPI service that captures raw data (Webhooks, Files, Logs)
and buffers it into a Postgres raw_lake table. Also provides Interoception
(System Vitals) via psutil.
"""

import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import asyncpg
import psutil
import structlog
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request

# --- Configuration ---
API_KEY = os.getenv("SOMA_INGRESS_KEY", "sigma-dev-secret-key")
DB_DSN = os.getenv("SOMA_PG_DSN", "postgresql://omega_user:omega_dev_password@localhost:6000/soma_sensory_lake")
PORT = int(os.getenv("SOMA_INGRESS_PORT", "8000"))
HOST = "0.0.0.0"

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Modern lifespan handler for DB pool management."""
    try:
        app.state.pool = await asyncpg.create_pool(DB_DSN)
        log.info("ingress_db_connected")
    except Exception as e:
        log.critical("ingress_db_failed", error=str(e))
        app.state.pool = None

    yield

    if hasattr(app.state, "pool") and app.state.pool:
        await app.state.pool.close()
        log.info("ingress_db_disconnected")


app = FastAPI(title="Soma.InGress (The Senses)", version="1.1", lifespan=lifespan)


async def persist_to_lake(source: str, event_type: str, payload: Dict[str, Any], client_ip: str = "unknown") -> str:
    """Persist incoming data to the raw_lake buffer table.

    Args:
        source: Origin of data (obsidian, github, chrome, terminal)
        event_type: Type of event (file_mod, push, web_capture, command_log)
        payload: JSON payload to store
        client_ip: IP address of the client

    Returns:
        The UUID of the inserted record
    """
    if not app.state.pool:
        raise HTTPException(503, "State Layer Disconnected")

    query = """
        INSERT INTO raw_lake (source, event_type, payload, client_ip) 
        VALUES ($1, $2, $3, $4) 
        RETURNING id;
    """
    async with app.state.pool.acquire() as conn:
        # Convert dict to JSON string for stable JSONB insertion
        payload_json = json.dumps(payload)
        row_id = await conn.fetchval(query, source, event_type, payload_json, client_ip)
        log.info("sensation_captured", source=source, type=event_type, id=str(row_id))
        return str(row_id)


# =============================================================================
# Health Check
# =============================================================================
@app.get("/health")
def health() -> Dict[str, str]:
    """Basic health check endpoint."""
    return {"role": "Senses", "status": "online"}


# =============================================================================
# Interoception (System Vitals)
# =============================================================================
@app.get("/api/v1/system/vitals")
def system_vitals(x_api_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Provides real-time CPU, RAM, and Disk telemetry."""
    if x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")

    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu": {"percent": cpu, "cores": psutil.cpu_count()},
        "memory": {
            "percent": mem.percent,
            "available_mb": mem.available // (1024 * 1024),
        },
        "disk": {
            "percent": disk.percent,
            "free_gb": disk.free // (1024 * 1024 * 1024),
        },
    }


# =============================================================================
# Exteroception (Data Capture)
# =============================================================================
@app.post("/api/v1/vault/sync")
async def ingest_vault(request: Request, x_api_key: Optional[str] = Header(None)) -> Dict[str, str]:
    """Capture Obsidian vault file modifications."""
    if x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")
    return {
        "status": "captured",
        "ref": await persist_to_lake("obsidian", "file_mod", await request.json(), request.client.host),
    }


@app.post("/api/v1/webhook/github")
async def ingest_github(request: Request) -> Dict[str, str]:
    """Capture GitHub webhook events."""
    return {
        "status": "captured",
        "ref": await persist_to_lake(
            "github",
            request.headers.get("X-GitHub-Event", "unknown"),
            await request.json(),
            request.client.host,
        ),
    }


@app.post("/api/v1/webhook/linear")
async def ingest_linear(request: Request) -> Dict[str, str]:
    """Capture Linear webhook events."""
    return {
        "status": "captured",
        "ref": await persist_to_lake(
            "linear",
            request.headers.get("Linear-Event", "unknown"),
            await request.json(),
            request.client.host,
        ),
    }


@app.post("/api/v1/chrome/capture")
async def ingest_chrome(request: Request, x_api_key: Optional[str] = Header(None)) -> Dict[str, str]:
    """Capture Chrome extension web captures."""
    if x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")
    return {
        "status": "captured",
        "ref": await persist_to_lake("chrome", "web_capture", await request.json(), request.client.host),
    }


@app.post("/api/v1/terminal/ghost")
async def ingest_terminal(request: Request, x_api_key: Optional[str] = Header(None)) -> Dict[str, str]:
    """Capture terminal command logs (Ghost integration)."""
    if x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")
    return {
        "status": "captured",
        "ref": await persist_to_lake("terminal", "command_log", await request.json(), request.client.host),
    }


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
