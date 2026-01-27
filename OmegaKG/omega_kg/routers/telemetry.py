import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any

import redis.asyncio as redis
from fastapi import APIRouter, Request, Query
from sse_starlette.sse import EventSourceResponse

from omega_kg.settings import settings

router = APIRouter(prefix="/api/v1/telemetry", tags=["Observability"])
logger = logging.getLogger(__name__)


async def event_generator(
    request: Request, session_id: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Generate SSE events by polling Redis for session state.
    """
    if not settings.redis_url:
        logger.warning("Redis URL not configured. Telemetry stream disabled.")
        yield {
            "event": "error",
            "data": json.dumps({"message": "Redis not configured"}),
        }
        return

    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info(f"Connected to Redis for telemetry stream: {session_id}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"message": "Redis connection failed"}),
        }
        return

    scratch_key = f"memos:{session_id}:scratch"
    working_key = f"memos:{session_id}:working"

    try:
        while True:
            if await request.is_disconnected():
                logger.info(f"Client disconnected from telemetry stream: {session_id}")
                break

            # Fetch data from Redis
            scratchpad = await redis_client.lrange(scratch_key, 0, -1)
            working_memory = await redis_client.hgetall(working_key)

            # Construct payload
            payload = {
                "scratchpad": scratchpad,
                "working_memory": working_memory,
                "timestamp": asyncio.get_event_loop().time(),  # Or system time
            }

            yield {"event": "message", "data": json.dumps(payload)}

            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info(f"Telemetry stream cancelled: {session_id}")
    except Exception as e:
        logger.error(f"Error in telemetry stream: {e}")
        yield {"event": "error", "data": json.dumps({"message": str(e)})}
    finally:
        await redis_client.aclose()


@router.get("/stream")
async def stream_telemetry(
    request: Request,
    session_id: str = Query("default_session", description="Session ID to monitor"),
):
    """
    Stream real-time telemetry data (scratchpad, working memory) via SSE.
    """
    logger.info(f"Starting telemetry stream for session: {session_id}")
    return EventSourceResponse(event_generator(request, session_id))
