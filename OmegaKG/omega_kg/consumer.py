"""
Soma OmegaKG Consumer: The Brain's Intake Valve.

Consumes Knowledge Digests from Redis 'soma_working_memory' stream,
vectorizes them via Docker Model Runner, and persists to Neo4j.

Architecture:
- XREAD from soma_working_memory (blocking)
- Generate 768-dim embeddings via EMBED_BASE_URL
- MERGE into Neo4j with (.text, .embedding, .source_id)

Only OmegaKG has Neo4j WRITE authorization.
"""

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
import redis.asyncio as redis
import structlog
from neo4j import AsyncGraphDatabase

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

# Neo4j Config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")  # No default - required in production

# Embedding Config (Docker Model Runner)
EMBED_BASE_URL = os.getenv(
    "EMBED_BASE_URL", "http://localhost:12434"
)  # Docker Model Runner default
EMBED_MODEL = os.getenv("EMBED_MODEL", "ai/qwen3-embedding:0.6B-F16")
EMBED_DIMENSION = int(os.getenv("SOMA_EMBED_DIMENSION", "768"))

# Consumer Config
CONSUMER_GROUP = "omegakg_brain"
CONSUMER_NAME = f"brain_consumer_{os.getpid()}"
BATCH_SIZE = 10
BLOCK_MS = 5000


class BrainConsumer:
    """The Brain's primary intake - consumes facts and persists knowledge."""

    def __init__(self):
        self._running = False
        self._redis: Optional[redis.Redis] = None
        self._neo4j_driver = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Initialize connections and start consuming."""
        log.info("brain_consumer_initializing", stream=WORKING_MEMORY_STREAM)

        # Connect to Redis
        self._redis = redis.from_url(REDIS_URL)

        # Connect to Neo4j (apexsigma.neo4j.soma)
        self._neo4j_driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )

        # HTTP client for embeddings (disable SSL verify for local Ollama)
        self._http_client = httpx.AsyncClient(timeout=30.0, verify=False)

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
        log.info("brain_consumer_active", status="LISTENING_TO_NERVOUS_SYSTEM")

        await self._consume_loop()

    async def stop(self) -> None:
        """Graceful shutdown."""
        log.info("brain_consumer_stopping")
        self._running = False

        if self._http_client:
            await self._http_client.aclose()
        if self._neo4j_driver:
            await self._neo4j_driver.close()
        if self._redis:
            await self._redis.close()

    async def _consume_loop(self) -> None:
        """Main consumption loop - XREAD from Redis stream."""
        assert self._redis is not None

        while self._running:
            try:
                # XREADGROUP for consumer group pattern
                messages = await self._redis.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    streams={WORKING_MEMORY_STREAM: ">"},
                    count=BATCH_SIZE,
                    block=BLOCK_MS,
                )

                if not messages:
                    continue

                for stream_name, stream_messages in messages:
                    for msg_id, msg_data in stream_messages:
                        await self._process_digest(msg_id, msg_data)

            except asyncio.CancelledError:
                log.info("consumer_loop_cancelled")
                break
            except Exception as e:
                log.error("consumer_loop_error", error=str(e))
                await asyncio.sleep(5)

    async def _process_digest(
        self,
        msg_id: bytes | str,
        msg_data: Dict[bytes | str, bytes | str],
    ) -> None:
        """Process a single Knowledge Digest from the stream."""
        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else msg_id

        try:
            # Parse payload
            payload_raw = msg_data.get(b"payload") or msg_data.get("payload")
            if isinstance(payload_raw, bytes):
                payload_raw = payload_raw.decode()

            if payload_raw is None:
                raise ValueError("Message has no payload")

            digest = json.loads(payload_raw)

            log.debug(
                "processing_digest",
                message_id=msg_id_str,
                source_id=digest.get("source_id"),
            )

            # Extract data from digest
            source_id = digest.get("source_id")
            source = digest.get("source", "unknown")

            # InGest sends text directly, not in fact_units array
            text = digest.get("text", "")
            metadata_dict = digest.get("metadata", {})
            entropy = metadata_dict.get("original_entropy", 0.0)

            if not text:
                log.warning("digest_has_no_text", message_id=msg_id_str)
                # Still ACK to avoid infinite loop
                assert self._redis is not None
                await self._redis.xack(WORKING_MEMORY_STREAM, CONSUMER_GROUP, msg_id)
                return

            # Generate embedding
            embedding = await self._vectorize(text)

            # MERGE into Neo4j
            node_id = await self._merge_to_neo4j(
                text=text,
                embedding=embedding,
                source_id=source_id,
                source=source,
                metadata=digest,
            )

            log.info(
                "fact_persisted",
                message_id=msg_id_str,
                source_id=source_id,
                node_id=node_id,
                entropy=entropy,
            )

            # ACK the message
            assert self._redis is not None
            await self._redis.xack(WORKING_MEMORY_STREAM, CONSUMER_GROUP, msg_id)

        except Exception as e:
            log.error(
                "digest_processing_failed",
                message_id=msg_id_str,
                error=str(e),
            )
            # ACK to prevent infinite retries (DLQ handled by Stomach)
            assert self._redis is not None
            await self._redis.xack(WORKING_MEMORY_STREAM, CONSUMER_GROUP, msg_id)

    async def _vectorize(self, text: str) -> List[float]:
        """Generate embedding via Docker Model Runner / Ollama.

        Returns 768-dim vector (nomic-embed-text default).
        Falls back to zero vector on failure.
        """
        try:
            assert self._http_client is not None

            response = await self._http_client.post(
                f"{EMBED_BASE_URL}/api/embeddings",
                json={
                    "model": EMBED_MODEL,
                    "prompt": text,
                },
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["embedding"]

            log.debug(
                "embedding_generated", model=EMBED_MODEL, dimension=len(embedding)
            )

            return embedding

        except Exception as e:
            log.error("embedding_failed", error=str(e))
            # Return zero vector as fallback
            return [0.0] * EMBED_DIMENSION

    async def _merge_to_neo4j(
        self,
        text: str,
        embedding: List[float],
        source_id: str,
        source: str,
        metadata: Dict[str, Any],
    ) -> str:
        """MERGE an AtomicFact node into Neo4j using APOC.

        Mandatory properties:
        - .text (resolved fact text)
        - .embedding (768-dim vector)
        - .source_id (raw_lake UUID)
        """
        # Generate hash for deduplication
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        cypher = """
        MERGE (f:AtomicFact {text_hash: $text_hash})
        ON CREATE SET
            f.text = $text,
            f.embedding = $embedding,
            f.source_id = $source_id,
            f.source = $source,
            f.metadata = $metadata,
            f.created_at = datetime(),
            f.processed_at = datetime()
        ON MATCH SET
            f.processed_at = datetime(),
            f.embedding = $embedding
        RETURN elementId(f) as node_id
        """

        assert self._neo4j_driver is not None

        async with self._neo4j_driver.session() as session:
            result = await session.run(
                cypher,
                text_hash=text_hash,
                text=text,
                embedding=embedding,
                source_id=source_id,
                source=source,
                metadata=json.dumps(metadata),
            )
            record = await result.single()
            return record["node_id"] if record else "unknown"


if __name__ == "__main__":
    consumer = BrainConsumer()
    try:
        asyncio.run(consumer.start())
    except KeyboardInterrupt:
        log.info("brain_consumer_shutdown", reason="user_interrupt")
