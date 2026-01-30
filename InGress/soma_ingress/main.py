"""Soma.InGress - The Senses Layer.

A lightweight FastAPI service that captures raw data (Webhooks, Files, Logs)
and buffers it into a Postgres raw_lake table. Also provides Interoception
(System Vitals) via psutil.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import asyncpg
import psutil
import redis.asyncio as redis
import structlog
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

# --- Configuration ---
API_KEY = os.getenv("SOMA_INGRESS_KEY")
DB_DSN = os.getenv("SOMA_PG_DSN")
PORT = int(os.getenv("SOMA_INGRESS_PORT", "8000"))
HOST = "0.0.0.0"

# Validate required environment variables
if not API_KEY:
    raise RuntimeError(
        "SOMA_INGRESS_KEY environment variable is required. Run: $env:SOMA_INGRESS_KEY='your-secure-key'"
    )
if not DB_DSN:
    raise RuntimeError("SOMA_PG_DSN environment variable is required. Run: $env:SOMA_PG_DSN='postgresql://...'")

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


# =============================================================================
# Manual Ingestion (Agent/Test Interface)
# =============================================================================
@app.post("/api/v1/manual/ingest")
async def manual_ingest(request: Request, x_api_key: Optional[str] = Header(None)) -> Dict[str, str]:
    """Manual JSON ingestion for agent/test use.

    Accepts arbitrary JSON payloads and persists them to the raw_lake table.
    Used by memOS ingest_signal tool and for E2E testing.

    Expected body format:
    {
        "source": "manual",  # optional, defaults to "manual"
        "event_type": "agent_thought",  # optional, defaults to "agent_thought"
        "payload": { ... }  # the actual data to store
    }
    """
    if x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")

    body = await request.json()
    source = body.get("source", "manual")
    event_type = body.get("event_type", "agent_thought")
    payload = body.get("payload", body)  # Use entire body if no payload key

    log.info("manual_ingestion", source=source, event_type=event_type)

    return {
        "status": "captured",
        "ref": await persist_to_lake(source, event_type, payload, request.client.host),
    }


# =============================================================================
# Neural Telemetry Stream (SSE)
# =============================================================================
@app.get("/api/v1/telemetry/stream")
async def stream_neural_pulse(request: Request) -> EventSourceResponse:
    """Broadcasts the Redis soma_working_memory stream to the Cortex Bridge UI.

    Streams real-time digestion events from the Stomach layer to the dashboard.
    Uses Server-Sent Events (SSE) for persistent connection.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6380/0"), decode_responses=True)

        try:
            last_id = "$"  # Start from now (newest messages)

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    log.info("telemetry_client_disconnected")
                    break

                # Read from working memory stream
                data = await redis_client.xread(
                    {"soma_working_memory": last_id},
                    count=1,
                    block=1000,  # Block for 1 second
                )

                if data:
                    for stream_name, messages in data:
                        for msg_id, payload in messages:
                            # Extract the digest payload
                            if "payload" in payload:
                                event_data = json.dumps(payload)
                                yield f"data: {event_data}\n\n"
                                last_id = msg_id
                                log.info("telemetry_pulse_sent", msg_id=msg_id)
                else:
                    # Send keep-alive ping
                    yield ": ping\n\n"

                await asyncio.sleep(0.1)

        except Exception as e:
            log.error("telemetry_stream_error", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            await redis_client.close()

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
