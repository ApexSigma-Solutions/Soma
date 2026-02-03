"""Stream to Cortex Op - Redis Stream producer for digested memories.

Implements TN-SOMA-204: Push digested records to soma:digestion:stream
and update Postgres status to 'DIGESTED' only after XADD confirms.

This is Stage 2.3 of SimpleMem v2.0:
- Generate mem_hash (SHA256 of text)
- XADD to soma:digestion:stream
- Update raw_lake processing_status = 'DIGESTED'
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import redis.asyncio as redis
from dagster import AssetExecutionContext, Config, asset
from pydantic import Field

from ..resources import PostgresResource
from ...services.qwen_embedder import QwenEmbedder, OLLAMA_BASE_URL, QWEN_MODEL

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv("SOMA_REDIS_URL", "redis://localhost:6380/0")
DIGESTION_STREAM = os.getenv("SOMA_DIGESTION_STREAM", "soma:digestion:stream")


class StreamConfig(Config):
    """Configuration for stream production."""

    redis_url: str = Field(default=REDIS_URL, description="Redis URL")
    stream_name: str = Field(default=DIGESTION_STREAM, description="Target stream")


@asset(
    description="Embed records and stream to cortex for Neo4j persistence",
    compute_kind="redis",
    group_name="digestion_pipeline",
    deps=["raw_conversations"],
)
async def stream_to_cortex(
    context: AssetExecutionContext,
    config: StreamConfig,
    postgres: PostgresResource,
    raw_conversations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Process raw records through embedding and stream to Redis.

    Implements the "Enzyme Action" stage:
    1. For each record, generate embedding via Qwen3
    2. Compute mem_hash (SHA256[:16] of text)
    3. XADD to soma:digestion:stream with {mem_hash, vector, text, source, timestamp}
    4. Only after XADD succeeds, UPDATE raw_lake SET processing_status = 'DIGESTED'

    This ensures at-least-once delivery with idempotent consumption.

    Returns:
        Summary dict with processed/failed counts
    """
    if not raw_conversations:
        context.log.info("No records to stream")
        return {"processed": 0, "failed": 0, "skipped": len(raw_conversations)}

    context.log.info(
        f"Streaming {len(raw_conversations)} records to {config.stream_name}"
    )

    processed = 0
    failed = 0

    # Initialize connections
    redis_client = redis.from_url(config.redis_url)
    conn = await postgres.get_connection()

    try:
        async with QwenEmbedder(base_url=OLLAMA_BASE_URL, model=QWEN_MODEL) as embedder:
            for record in raw_conversations:
                record_id = record["id"]
                try:
                    # Extract text from payload
                    payload = record["payload"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)

                    # Get text content - try common fields
                    text = (
                        payload.get("text")
                        or payload.get("content")
                        or payload.get("message")
                        or json.dumps(payload)
                    )

                    # 1. Generate embedding
                    vector = await embedder.embed(text)

                    # 2. Compute mem_hash (per SimpleMem v2.0)
                    mem_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

                    # 3. XADD to stream
                    stream_entry = {
                        "mem_hash": mem_hash,
                        "vector": json.dumps(vector),
                        "text": text[:10000],  # Limit text size for Redis
                        "source": record["source"],
                        "event_type": record["event_type"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": json.dumps(
                            {
                                "text": text,
                                "metadata": {
                                    "source": record["source"],
                                    "event_type": record["event_type"],
                                    "client_ip": record.get("client_ip", "unknown"),
                                    "raw_lake_id": record_id,
                                },
                            }
                        ),
                    }

                    msg_id = await redis_client.xadd(
                        config.stream_name,
                        stream_entry,
                    )

                    context.log.debug(f"XADD success: {msg_id} for record {record_id}")

                    # 4. Only update Postgres AFTER Redis confirms
                    await conn.execute(
                        """
                        UPDATE raw_lake 
                        SET processing_status = 'DIGESTED',
                            processed_at = NOW()
                        WHERE id = $1
                        """,
                        record_id,
                    )

                    processed += 1
                    context.log.info(
                        f"Digested record {record_id}",
                        extra={"mem_hash": mem_hash, "stream_id": str(msg_id)},
                    )

                except Exception as e:
                    failed += 1
                    context.log.error(f"Failed to digest record {record_id}: {e}")

                    # Mark as error in Postgres
                    await conn.execute(
                        """
                        UPDATE raw_lake 
                        SET processing_status = 'ERROR',
                            last_error = $1
                        WHERE id = $2
                        """,
                        str(e),
                        record_id,
                    )

    finally:
        await redis_client.close()
        await conn.close()

    context.log.info(f"Stream complete: {processed} processed, {failed} failed")

    return {
        "processed": processed,
        "failed": failed,
        "stream": config.stream_name,
    }
