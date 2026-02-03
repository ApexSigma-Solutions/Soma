import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional

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


# =============================================================================
# Brain Metrics Telemetry (TN-CTX-201/203)
# =============================================================================


async def brain_metrics_generator(
    request: Request,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Generate SSE events with Brain (OmegaKG) metrics from Neo4j.

    Queries the knowledge graph for:
    - Total node count (AtomicFacts)
    - Average connectivity (relationships per node)
    - Embedding dimension (768 for Qwen3)
    """
    # Check if Neo4j driver is available in app state
    if not hasattr(request.state, "neo4j_driver") or not request.state.neo4j_driver:
        yield {
            "event": "error",
            "data": json.dumps({"message": "Neo4j not connected"}),
        }
        return

    driver = request.state.neo4j_driver

    try:
        while True:
            if await request.is_disconnected():
                logger.info("Client disconnected from brain metrics stream")
                break

            try:
                # Query Neo4j for metrics
                async with driver.session() as session:
                    # Get total node count
                    node_result = await session.run(
                        "MATCH (n) RETURN count(n) as node_count"
                    )
                    node_record = await node_result.single()
                    node_count = node_record["node_count"] if node_record else 0

                    # Get average connectivity
                    conn_result = await session.run(
                        """
                        MATCH ()-[r]->()
                        RETURN count(r) as rel_count
                        """
                    )
                    conn_record = await conn_result.single()
                    rel_count = conn_record["rel_count"] if conn_record else 0
                    avg_connectivity = rel_count / node_count if node_count > 0 else 0

                    # Get embedding dimension from settings (or query)
                    embedding_dimension = 768  # Qwen3 default

                    # Construct payload
                    payload = {
                        "node_count": node_count,
                        "avg_connectivity": round(avg_connectivity, 2),
                        "embedding_dimension": embedding_dimension,
                        "timestamp": datetime.now().isoformat(),
                    }

                    yield {
                        "event": "brain_pulse",
                        "data": json.dumps(payload),
                    }

            except Exception as e:
                logger.error(f"Error querying brain metrics: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"message": str(e)}),
                }

            await asyncio.sleep(2.0)  # Update every 2 seconds

    except asyncio.CancelledError:
        logger.info("Brain metrics stream cancelled")
    except Exception as e:
        logger.error(f"Error in brain metrics stream: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"message": str(e)}),
        }


@router.get("/brain")
async def stream_brain_metrics(request: Request):
    """
    Stream real-time Brain (OmegaKG) metrics via SSE.

    Returns:
        SSE stream with node_count, avg_connectivity, and embedding_dimension.
    """
    logger.info("Starting brain metrics stream")
    return EventSourceResponse(brain_metrics_generator(request))
