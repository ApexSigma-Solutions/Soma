"""Stream Consumer Worker for OmegaKG.

Consumes Atomic Facts from the soma_working_memory Redis stream,
generates embeddings via Docker Model Runner, and MERGEs into Neo4j.

This implements the "Brain" checkpoint in the Soma Meal Trace:
Redis Stream -> Embedding -> Neo4j Graph

Pattern inspired by JanitorWorker in memOS.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import redis.asyncio as redis
import structlog
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel

# Configuration
LOG_LEVEL = os.getenv("SOMA_LOG_LEVEL", "INFO")
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, LOG_LEVEL)),
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

# Redis Config
REDIS_URL = os.getenv("SOMA_REDIS_URL", "redis://localhost:6380/0")
WORKING_MEMORY_STREAM = os.getenv("SOMA_WORKING_MEMORY_STREAM", "soma_working_memory")
DLQ_STREAM = f"{WORKING_MEMORY_STREAM}:dlq"

# Docker Model Runner Config (injected by docker-compose models block)
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://model-runner.docker.internal")
EMBED_MODEL = os.getenv("EMBED_MODEL", "ai/qwen3-embedding:0.6B-F16")
EMBED_DIMENSION = int(os.getenv("SOMA_EMBED_DIMENSION", "1024"))

# Neo4j Config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Consumer Config
CONSUMER_GROUP = os.getenv("SOMA_CONSUMER_GROUP", "omegakg_consumers")
CONSUMER_NAME = os.getenv("SOMA_CONSUMER_NAME", f"consumer_{os.getpid()}")
BATCH_SIZE = int(os.getenv("SOMA_CONSUMER_BATCH_SIZE", "10"))
BLOCK_MS = int(os.getenv("SOMA_CONSUMER_BLOCK_MS", "5000"))


class AtomicFactNode(BaseModel):
    """Pydantic model for Neo4j AtomicFact node."""

    text: str
    text_hash: str
    metadata: Dict[str, Any]
    embedding: List[float]
    source: str
    event_type: str
    created_at: datetime
    processed_at: datetime


class StreamConsumer:
    """Consumes Atomic Facts from Redis and persists to Neo4j.

    Responsibilities:
    1. XREAD from soma_working_memory stream
    2. Generate embeddings via Docker Model Runner
    3. MERGE into Neo4j with .text, .metadata, .embedding
    4. Handle failures via DLQ
    """

    def __init__(self):
        """Initialize consumer with connections."""
        self._running = False
        self._redis: Optional[redis.Redis] = None
        self._neo4j_driver = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self.last_id = ">"  # Read only new messages

    async def start(self) -> None:
        """Start the consumer worker."""
        log.info(
            "stream_consumer_starting",
            stream=WORKING_MEMORY_STREAM,
            consumer_group=CONSUMER_GROUP,
            consumer_name=CONSUMER_NAME,
        )

        # Initialize connections
        self._redis = redis.from_url(REDIS_URL)
        self._neo4j_driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        self._http_client = httpx.AsyncClient(timeout=30.0)

        # Ensure consumer group exists
        try:
            await self._redis.xgroup_create(
                WORKING_MEMORY_STREAM,
                CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )
            log.info("consumer_group_created", group=CONSUMER_GROUP)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            log.debug("consumer_group_exists", group=CONSUMER_GROUP)

        self._running = True
        await self._consume_loop()

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        log.info("stream_consumer_stopping")
        self._running = False

        if self._http_client:
            await self._http_client.aclose()
        if self._neo4j_driver:
            await self._neo4j_driver.close()
        if self._redis:
            await self._redis.close()

    async def _consume_loop(self) -> None:
        """Main consumption loop."""
        assert self._redis is not None, "Redis client not initialized"

        while self._running:
            try:
                # XREADGROUP for consumer group pattern
                messages = await self._redis.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    streams={WORKING_MEMORY_STREAM: self.last_id},
                    count=BATCH_SIZE,
                    block=BLOCK_MS,
                )

                if not messages:
                    continue

                for stream_name, stream_messages in messages:
                    for msg_id, msg_data in stream_messages:
                        await self._process_message(msg_id, msg_data)

            except asyncio.CancelledError:
                log.info("consumer_loop_cancelled")
                break
            except Exception as e:
                log.error("consumer_loop_error", error=str(e))
                await asyncio.sleep(5)  # Back off on error

    async def _process_message(
        self,
        msg_id: bytes | str,
        msg_data: Dict[bytes | str, bytes | str],
    ) -> None:
        """Process a single message from the stream."""
        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else msg_id

        try:
            # Parse payload
            payload_raw = msg_data.get(b"payload") or msg_data.get("payload")
            if isinstance(payload_raw, bytes):
                payload_raw = payload_raw.decode()

            if payload_raw is None:
                raise ValueError("Message has no payload field")

            atomic_fact = json.loads(payload_raw)

            log.debug(
                "processing_atomic_fact",
                message_id=msg_id_str,
                source=atomic_fact.get("metadata", {}).get("source", "unknown"),
            )

            # 1. Generate embedding
            text = atomic_fact.get("text", "")
            embedding = await self._generate_embedding(text)

            # 2. MERGE into Neo4j
            node_id = await self._merge_to_neo4j(atomic_fact, embedding)

            # 3. ACK the message
            assert self._redis is not None
            await self._redis.xack(WORKING_MEMORY_STREAM, CONSUMER_GROUP, msg_id)

            log.info(
                "atomic_fact_persisted",
                message_id=msg_id_str,
                neo4j_node_id=node_id,
                embedding_dim=len(embedding),
            )

        except Exception as e:
            log.error(
                "message_processing_failed",
                message_id=msg_id_str,
                error=str(e),
            )

            # Send to DLQ
            await self._send_to_dlq(msg_id_str, msg_data, str(e))

            # ACK to prevent reprocessing (DLQ handles retry)
            assert self._redis is not None
            await self._redis.xack(WORKING_MEMORY_STREAM, CONSUMER_GROUP, msg_id)

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding via Docker Model Runner.

        Uses the OpenAI-compatible embeddings API.
        """
        try:
            assert self._http_client is not None, "HTTP client not initialized"
            response = await self._http_client.post(
                f"{EMBED_BASE_URL}/v1/embeddings",
                json={
                    "input": text,
                    "model": EMBED_MODEL,
                },
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]

            log.debug(
                "embedding_generated",
                model=EMBED_MODEL,
                dimension=len(embedding),
            )

            return embedding

        except Exception as e:
            log.error("embedding_generation_failed", error=str(e))
            # Return zero vector as fallback (will be re-embedded later)
            return [0.0] * EMBED_DIMENSION

    async def _merge_to_neo4j(
        self,
        atomic_fact: Dict[str, Any],
        embedding: List[float],
    ) -> str:
        """MERGE an AtomicFact node into Neo4j.

        Node properties:
        - text: The compressed text content
        - text_hash: SHA-256 hash for deduplication
        - metadata: JSONB metadata map
        - embedding: Vector for similarity search
        """
        text = atomic_fact.get("text", "")
        metadata = atomic_fact.get("metadata", {})

        # Generate hash for deduplication
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        cypher = """
        MERGE (f:AtomicFact {text_hash: $text_hash})
        ON CREATE SET
            f.text = $text,
            f.metadata = $metadata,
            f.embedding = $embedding,
            f.source = $source,
            f.event_type = $event_type,
            f.created_at = datetime(),
            f.processed_at = datetime()
        ON MATCH SET
            f.processed_at = datetime(),
            f.embedding = $embedding
        RETURN elementId(f) as node_id
        """

        async with self._neo4j_driver.session() as session:
            result = await session.run(
                cypher,
                text_hash=text_hash,
                text=text,
                metadata=json.dumps(metadata),  # Neo4j stores as string
                embedding=embedding,
                source=metadata.get("source", "unknown"),
                event_type=metadata.get("event_type", "unknown"),
            )
            record = await result.single()
            return record["node_id"] if record else "unknown"

    async def _send_to_dlq(
        self,
        msg_id: str,
        msg_data: Dict,
        error: str,
    ) -> None:
        """Send failed message to Dead Letter Queue."""
        try:
            dlq_entry = {
                "original_id": msg_id,
                "payload": msg_data.get(b"payload") or msg_data.get("payload", ""),
                "error": error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

            # Decode bytes if needed
            if isinstance(dlq_entry["payload"], bytes):
                dlq_entry["payload"] = dlq_entry["payload"].decode()

            assert self._redis is not None
            await self._redis.xadd(
                DLQ_STREAM, {k: str(v) for k, v in dlq_entry.items()}
            )

            log.warning(
                "message_sent_to_dlq",
                original_id=msg_id,
                dlq_stream=DLQ_STREAM,
            )

        except Exception as e:
            log.critical(
                "dlq_send_failed",
                original_id=msg_id,
                error=str(e),
            )


# Factory function for lifespan integration
_consumer_instance: Optional[StreamConsumer] = None


async def get_stream_consumer() -> StreamConsumer:
    """Get or create the singleton stream consumer."""
    global _consumer_instance
    if _consumer_instance is None:
        _consumer_instance = StreamConsumer()
    return _consumer_instance


async def start_stream_consumer() -> None:
    """Start the stream consumer (for use in lifespan)."""
    consumer = await get_stream_consumer()
    asyncio.create_task(consumer.start())


async def stop_stream_consumer() -> None:
    """Stop the stream consumer (for use in lifespan)."""
    global _consumer_instance
    if _consumer_instance:
        await _consumer_instance.stop()
        _consumer_instance = None


if __name__ == "__main__":
    # Standalone mode for testing
    consumer = StreamConsumer()
    try:
        asyncio.run(consumer.start())
    except KeyboardInterrupt:
        log.info("consumer_shutdown", reason="user_interrupt")
