"""Stream to Cortex Op - Redis Stream producer for digested memories.

TN-SOMA-303: Simplified Digestion - delegates cognitive processing to OmegaKG Guardian.

Graph Native Cloud Architecture:
- Primary: POST text to OmegaKG Guardian /ingest endpoint for LLM extraction + embedding
- Fallback: Local QwenEmbedder if OmegaKG is offline (per user requirement)
- Redis stream entry simplified to {text, source, metadata}
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
import redis.asyncio as redis
from dagster import AssetExecutionContext, Config, asset
from pydantic import Field

from ..resources import PostgresResource
from ...services.qwen_embedder import QwenEmbedder, EMBED_BASE_URL, EMBED_MODEL

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv("SOMA_REDIS_URL", "redis://localhost:6380/0")
DIGESTION_STREAM = os.getenv("SOMA_DIGESTION_STREAM", "soma:digestion:stream")

# OmegaKG Guardian Configuration (TN-SOMA-303)
OMEGAKG_URL = os.getenv("OMEGA_KG_URL", "http://localhost:8765")
SOMA_INTERNAL_KEY = os.getenv("SOMA_INTERNAL_KEY", "")


class StreamConfig(Config):
    """Configuration for stream production."""

    redis_url: str = Field(default=REDIS_URL, description="Redis URL")
    stream_name: str = Field(default=DIGESTION_STREAM, description="Target stream")
    omegakg_url: str = Field(default=OMEGAKG_URL, description="OmegaKG Guardian URL")


async def _ingest_via_guardian(
    text: str, source: str, metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Send text to OmegaKG Guardian /ingest endpoint for cognitive processing.

    Args:
        text: Content to process
        source: Origin of content
        metadata: Additional metadata

    Returns:
        Response from OmegaKG Guardian

    Raises:
        httpx.HTTPError: If request fails
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OMEGAKG_URL}/guardian/ingest",
            json={"text": text, "source": source, "metadata": metadata},
            headers={"X-Soma-Key": SOMA_INTERNAL_KEY},
        )
        response.raise_for_status()
        return response.json()


async def _embed_local_fallback(text: str) -> List[float]:
    """Fallback: Generate embedding locally via Docker Model Runner.

    Called when OmegaKG Guardian is unavailable.
    """
    async with QwenEmbedder(base_url=EMBED_BASE_URL, model=EMBED_MODEL) as embedder:
        return await embedder.embed(text)


@asset(
    description="Process records via OmegaKG Guardian and stream to Redis",
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
    """Process raw records through OmegaKG Guardian and stream to Redis.

    TN-SOMA-303: Simplified Digestion with Guardian fallback pattern:
    1. Extract text from record
    2. Try OmegaKG Guardian /ingest (handles LLM + embedding + Neo4j persistence)
    3. If Guardian offline: local embedding fallback + XADD to Redis
    4. Update Postgres status

    Returns:
        Summary dict with processed/failed counts
    """
    if not raw_conversations:
        context.log.info("No records to stream")
        return {"processed": 0, "failed": 0, "skipped": 0, "fallback_used": 0}

    context.log.info(
        f"Streaming {len(raw_conversations)} records (Guardian primary, local fallback)"
    )

    processed = 0
    failed = 0
    fallback_used = 0

    # Initialize connections
    redis_client = redis.from_url(config.redis_url)
    conn = await postgres.get_connection()

    try:
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

                source = record["source"]
                metadata = {
                    "event_type": record["event_type"],
                    "client_ip": record.get("client_ip", "unknown"),
                    "raw_lake_id": record_id,
                }

                # Compute mem_hash (per SimpleMem v2.0)
                mem_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

                # === Primary: OmegaKG Guardian ===
                guardian_success = False
                try:
                    result = await _ingest_via_guardian(text, source, metadata)
                    if result.get("success"):
                        guardian_success = True
                        context.log.info(
                            f"Guardian processed: {record_id}",
                            extra={
                                "nodes": result.get("nodes_created", 0),
                                "edges": result.get("edges_created", 0),
                            },
                        )
                except Exception as e:
                    context.log.warning(
                        f"Guardian offline, using local fallback: {e}"
                    )

                # === Fallback: Local embedding + Redis XADD ===
                if not guardian_success:
                    fallback_used += 1
                    try:
                        vector = await _embed_local_fallback(text)
                    except Exception as embed_err:
                        context.log.error(f"Local embedding failed: {embed_err}")
                        vector = []  # Empty vector as last resort

                    # XADD to Redis for later processing
                    stream_entry = {
                        "mem_hash": mem_hash,
                        "vector": json.dumps(vector) if vector else "",
                        "text": text[:10000],  # Limit text size for Redis
                        "source": source,
                        "metadata": json.dumps(metadata),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "fallback": "true",
                    }

                    msg_id = await redis_client.xadd(
                        config.stream_name,
                        stream_entry,
                    )
                    context.log.debug(
                        f"XADD (fallback) success: {msg_id} for record {record_id}"
                    )

                # Update Postgres status
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
                    extra={"mem_hash": mem_hash, "via": "guardian" if guardian_success else "fallback"},
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

    context.log.info(
        f"Stream complete: {processed} processed, {failed} failed, {fallback_used} fallback"
    )

    return {
        "processed": processed,
        "failed": failed,
        "fallback_used": fallback_used,
        "stream": config.stream_name,
    }
