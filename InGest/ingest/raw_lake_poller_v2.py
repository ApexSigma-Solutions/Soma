"""
Soma InGest Service: The Stomach.

Standalone poller implementing SimpleMem Stage 1 Compression.
Polls raw_lake from InGress and digests signals into Atomic Facts.

This is THE WORKHORSE - all metabolic heavy lifting happens here.
"""

import asyncio
import json
import logging
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import asyncpg
import redis.asyncio as redis
import structlog

# =============================================================================
# Configuration (All via env vars for future UI config)
# =============================================================================
LOG_LEVEL = os.getenv("SOMA_LOG_LEVEL", "INFO")
PG_DSN = os.getenv(
    "SOMA_PG_DSN",
    "postgresql://omega_user:omega_dev_password@localhost:6000/soma_sensory_lake",
)
REDIS_URL = os.getenv("SOMA_REDIS_URL", "redis://localhost:6380/0")
SOMA_KEY = os.getenv("SOMA_INGRESS_KEY", "sigma-dev-secret-key")

# Polling config
POLL_INTERVAL = int(os.getenv("STOMACH_POLL_INTERVAL", "5"))
BATCH_SIZE = int(os.getenv("STOMACH_BATCH_SIZE", "10"))
MAX_RETRIES = int(os.getenv("STOMACH_MAX_RETRIES", "3"))

# SimpleMem config
ENTROPY_THRESHOLD = float(os.getenv("SIMPLEMEM_ENTROPY_THRESHOLD", "0.35"))

# Stream config
WORKING_MEMORY_STREAM = os.getenv("SOMA_WORKING_MEMORY_STREAM", "soma_working_memory")

# Configure structlog
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


# =============================================================================
# SimpleMem Stage 1: Semantic Compression
# =============================================================================
def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of character distribution."""
    if not text:
        return 0.0
    freq = Counter(text.lower())
    length = len(text)
    return -sum((f / length) * math.log2(f / length) for f in freq.values())


def entropy_gate(text: str) -> tuple[bool, float]:
    """Apply entropy gate filter. Returns (passed, entropy_value)."""
    entropy = calculate_entropy(text)
    passed = entropy >= ENTROPY_THRESHOLD
    if not passed:
        log.debug(
            "entropy_gate_filtered",
            entropy=round(entropy, 4),
            threshold=ENTROPY_THRESHOLD,
        )
    return passed, entropy


def resolve_coreferences(text: str) -> str:
    """Resolve coreferences using spaCy + coreferee.

    Falls back to original text if coreferee not available.
    """
    try:
        import spacy

        if not hasattr(resolve_coreferences, "_nlp"):
            nlp = spacy.load("en_core_web_sm")
            try:
                nlp.add_pipe("coreferee")
                resolve_coreferences._nlp = nlp
                resolve_coreferences._has_coreferee = True
                log.info("coreferee_loaded")
            except Exception:
                resolve_coreferences._nlp = nlp
                resolve_coreferences._has_coreferee = False
                log.warning("coreferee_unavailable", fallback="entity_extraction_only")

        nlp = resolve_coreferences._nlp
        doc = nlp(text)

        if resolve_coreferences._has_coreferee and doc._.coref_chains:
            resolved_text = text
            for chain in doc._.coref_chains:
                mentions = [doc[m.root_index] for m in chain]
                main_mention = next(
                    (m.text for m in mentions if m.ent_type_ or m.pos_ == "PROPN"),
                    None,
                )
                if main_mention:
                    for mention in chain:
                        token = doc[mention.root_index]
                        if token.pos_ == "PRON":
                            resolved_text = re.sub(
                                rf"\b{re.escape(token.text)}\b",
                                main_mention,
                                resolved_text,
                                count=1,
                            )
            return resolved_text
        return text
    except Exception as e:
        log.warning("coreference_failed", error=str(e))
        return text


def anchor_temporal_references(text: str) -> str:
    """Convert relative time expressions to ISO-8601."""
    try:
        import dateparser

        patterns = [
            r"\b(yesterday|today|tomorrow)\b",
            r"\b(last|next)\s+(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            r"\b(in|after)\s+\d+\s+(hour|hours|day|days|week|weeks)\b",
            r"\b\d+\s+(hour|hours|day|days|week|weeks)\s+ago\b",
        ]

        now = datetime.now(timezone.utc)

        def replace_temporal(match: re.Match) -> str:
            parsed = dateparser.parse(
                match.group(0),
                settings={"RELATIVE_BASE": now, "TIMEZONE": "UTC"},
            )
            return parsed.strftime("%Y-%m-%dT%H:%M:%S%z") if parsed else match.group(0)

        result = text
        for pattern in patterns:
            result = re.sub(pattern, replace_temporal, result, flags=re.IGNORECASE)
        return result
    except Exception as e:
        log.warning("temporal_anchoring_failed", error=str(e))
        return text


# =============================================================================
# The Stomach Class
# =============================================================================
class Stomach:
    """The InGest Service Class: Handles the metabolic processing of raw data."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[redis.Redis] = None
        self._running = True

    async def initialize(self) -> None:
        """Initialize database and Redis connections."""
        self.pool = await asyncpg.create_pool(self.dsn)
        self.redis = redis.from_url(REDIS_URL)
        log.info("ingest_stomach_initialized", status="READY_TO_CHEW")

    async def digest_window(self, record: asyncpg.Record) -> Optional[Dict[str, Any]]:
        """SimpleMem Stage 1: Semantic Compression.

        Pipeline:
        1. Entropy Gate - filter low-information signals
        2. Coreference Resolution - replace pronouns with entity names
        3. Temporal Anchoring - convert relative time to ISO-8601
        4. Synthesize Atomic Fact
        """
        payload = (
            json.loads(record["payload"])
            if isinstance(record["payload"], str)
            else record["payload"]
        )

        # Extract text content
        text = (
            payload.get("message")
            or payload.get("content")
            or payload.get("text")
            or json.dumps(payload)
        )

        # 1. Entropy Gate
        passed, entropy = entropy_gate(text)
        if not passed:
            log.info("signal_filtered", id=str(record["id"]), reason="low_entropy")
            return None  # Filtered out

        # 2. Coreference Resolution
        resolved_text = resolve_coreferences(text)

        # 3. Temporal Anchoring
        anchored_text = anchor_temporal_references(resolved_text)

        # 4. Synthesize Atomic Fact (Knowledge Digest)
        digest = {
            "source_id": str(record["id"]),
            "source": record["source"],
            "event_type": record["event_type"],
            "text": anchored_text,
            "metadata": {
                "original_entropy": round(entropy, 4),
                "source": record["source"],
                "event_type": record["event_type"],
                "pipeline_version": "simplemem-1.0",
            },
            "compressed_at": datetime.now(timezone.utc).isoformat(),
        }

        log.info(
            "digestion_complete",
            id=str(record["id"]),
            entropy=round(entropy, 4),
            text_len=len(anchored_text),
        )

        return digest

    async def emit_to_redis(self, digest: Dict[str, Any]) -> str:
        """Pushes the Knowledge Digest to the Redis Working Memory Stream."""
        assert self.redis is not None

        msg_id = await self.redis.xadd(
            WORKING_MEMORY_STREAM,
            {
                "payload": json.dumps(digest),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            maxlen=10000,
        )

        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
        log.info(
            "nervous_system_pulse",
            stream=WORKING_MEMORY_STREAM,
            message_id=msg_id_str,
            source_id=digest["source_id"],
        )
        return msg_id_str

    async def send_to_dlq(self, record: asyncpg.Record, error: str) -> None:
        """Send failed record to Dead Letter Queue stream."""
        if self.redis is None:
            return

        dlq_stream = f"{WORKING_MEMORY_STREAM}:dlq"
        await self.redis.xadd(
            dlq_stream,
            {
                "source_id": str(record["id"]),
                "source": record["source"],
                "error": error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        log.warning("sent_to_dlq", id=str(record["id"]), stream=dlq_stream)

    async def poll_cycle(self) -> None:
        """Poll raw_lake and process a batch of unprocessed records."""
        assert self.pool is not None

        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT id, source, event_type, payload, retry_count 
                FROM raw_lake 
                WHERE processed = FALSE AND failed = FALSE AND retry_count < $1
                ORDER BY ingested_at ASC
                LIMIT $2
                """,
                MAX_RETRIES,
                BATCH_SIZE,
            )

            if not records:
                return

            for r in records:
                try:
                    digest = await self.digest_window(r)

                    if digest is not None:
                        # Successfully digested - emit to stream
                        await self.emit_to_redis(digest)

                    # Mark as processed (even if filtered by entropy gate)
                    await conn.execute(
                        "UPDATE raw_lake SET processed=TRUE, processed_at=NOW() WHERE id=$1",
                        r["id"],
                    )

                except Exception as e:
                    error_msg = str(e)
                    log.error("digestion_failure", id=str(r["id"]), error=error_msg)

                    # Update retry count and potentially mark as failed
                    new_retries = r["retry_count"] + 1
                    is_failed = new_retries >= MAX_RETRIES

                    await conn.execute(
                        """
                        UPDATE raw_lake 
                        SET retry_count=$1, failed=$2, last_error=$3 
                        WHERE id=$4
                        """,
                        new_retries,
                        is_failed,
                        error_msg,
                        r["id"],
                    )

                    if is_failed:
                        await self.send_to_dlq(r, error_msg)

    async def run_forever(self) -> None:
        """Main polling loop - runs until interrupted."""
        await self.initialize()

        log.info(
            "stomach_peristalsis_active",
            poll_interval=POLL_INTERVAL,
            batch_size=BATCH_SIZE,
            entropy_threshold=ENTROPY_THRESHOLD,
        )

        while self._running:
            try:
                await self.poll_cycle()
            except Exception as e:
                log.error("poll_cycle_error", error=str(e))

            await asyncio.sleep(POLL_INTERVAL)

        # Cleanup
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.close()

        log.info("stomach_hibernating")

    async def stop(self) -> None:
        """Signal the stomach to stop."""
        self._running = False


if __name__ == "__main__":
    stomach = Stomach(PG_DSN)
    try:
        asyncio.run(stomach.run_forever())
    except KeyboardInterrupt:
        log.info("stomach_shutdown", reason="user_interrupt")
