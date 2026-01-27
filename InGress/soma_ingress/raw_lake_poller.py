"""Soma Stomach Poller (Peristalsis) - Circuit Breaker Edition v2.0.

Polls soma_sensory_lake.raw_lake and delivers Knowledge Digests to OmegaKG.
Implements Circuit Breaker pattern to prevent cascading failures.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional

import asyncpg
import structlog

# Setup JSON Logging for Structlog Aggregation
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

# Config from Env (Standardized across Soma)
DB_DSN = os.getenv(
    "SOMA_PG_DSN",
    "postgresql://omega_user:omega_dev_password@localhost:6000/soma_sensory_lake",
)
OMEGAKG_URL = os.getenv("OMEGA_KG_URL", "http://localhost:8765/api/v1/ingest/digest")
POLL_INTERVAL = int(os.getenv("STOMACH_POLL_INTERVAL", "5"))  # Seconds
MAX_RETRIES = int(os.getenv("STOMACH_MAX_RETRIES", "3"))
BATCH_SIZE = int(os.getenv("STOMACH_BATCH_SIZE", "10"))

# Circuit Breaker Config
FAILURE_THRESHOLD = int(os.getenv("STOMACH_FAILURE_THRESHOLD", "5"))
COOLDOWN_PERIOD = int(os.getenv("STOMACH_COOLDOWN_SECONDS", "60"))


class CircuitBreaker:
    """Circuit Breaker implementation for Stomach Poller."""

    def __init__(self, failure_threshold: int, cooldown_seconds: int):
        """Initialize Circuit Breaker.

        Args:
            failure_threshold: Number of consecutive failures before tripping
            cooldown_seconds: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.cooldown_period = timedelta(seconds=cooldown_seconds)
        self.consecutive_failures = 0
        self.is_tripped = False
        self.tripped_at: Optional[datetime] = None

    def trip(self, reason: str) -> None:
        """Trip the circuit breaker."""
        if not self.is_tripped:
            self.is_tripped = True
            self.tripped_at = datetime.now()
            log.critical(
                "circuit_breaker_tripped",
                reason=reason,
                cooldown=f"{self.cooldown_period.total_seconds()}s",
            )

    def reset(self) -> None:
        """Reset the circuit breaker after successful operation."""
        if self.is_tripped:
            self.is_tripped = False
            self.tripped_at = None
            self.consecutive_failures = 0
            log.info("circuit_breaker_reset", status="PERISTALSIS_RESUMED")

    def can_attempt(self) -> bool:
        """Check if we can attempt processing.

        Returns:
            True if either not tripped or cooldown expired (half-open state)
        """
        if not self.is_tripped:
            return True

        # Check if cooldown period has elapsed (Half-Open state)
        if datetime.now() > self.tripped_at + self.cooldown_period:
            log.info("circuit_breaker_half_open", message="Attempting recovery batch...")
            return True

        return False

    def record_success(self) -> None:
        """Record a successful operation."""
        self.consecutive_failures = 0
        if self.is_tripped:
            self.reset()

    def record_failure(self) -> None:
        """Record a failed operation and trip if threshold reached."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.trip(f"Reached {self.failure_threshold} consecutive failures")


class Stomach:
    """Soma Stomach - Digestion engine with Circuit Breaker resilience."""

    def __init__(self, dsn: str):
        """Initialize Stomach with database connection.

        Args:
            dsn: PostgreSQL connection string
        """
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        self._running = True
        self.breaker = CircuitBreaker(FAILURE_THRESHOLD, COOLDOWN_PERIOD)

    async def deliver_to_omegakg(self, record: asyncpg.Record) -> bool:
        """Deliver digested knowledge to OmegaKG for Neo4j persistence.

        Args:
            record: Raw lake record to digest

        Returns:
            True if delivery successful
        """
        # TODO: Implement HTTP POST to OmegaKG
        # For now, simulate successful delivery
        await asyncio.sleep(0.1)
        log.info(
            "digest_delivered",
            id=str(record["id"]),
            source=record["source"],
            event_type=record["event_type"],
        )
        return True

    async def poll_and_digest(self) -> None:
        """Poll raw_lake and process batch with Circuit Breaker protection."""
        # 1. Check Circuit Status
        if not self.breaker.can_attempt():
            return  # Still in cooldown

        async with self.pool.acquire() as conn:
            # Fetch unprocessed, non-failed records within retry limit
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
                # No work to do - reset breaker if it was in half-open state
                if self.breaker.is_tripped:
                    self.breaker.reset()
                return

            batch_success = True
            for record in records:
                try:
                    # Deliver to OmegaKG (which handles Neo4j MERGE)
                    if await self.deliver_to_omegakg(record):
                        # Success Path
                        await conn.execute(
                            "UPDATE raw_lake SET processed=TRUE WHERE id=$1",
                            record["id"],
                        )
                        self.breaker.record_success()

                except Exception as e:
                    batch_success = False
                    self.breaker.record_failure()
                    error_msg = str(e)

                    # Update DLQ columns
                    new_retries = record["retry_count"] + 1
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
                        record["id"],
                    )
                    log.error(
                        "digestion_failed",
                        id=str(record["id"]),
                        retry=new_retries,
                        error=error_msg,
                    )

                    # If breaker tripped, stop processing this batch
                    if self.breaker.is_tripped:
                        break

            # If entire batch succeeded and we were in recovery, reset
            if batch_success and self.breaker.is_tripped:
                self.breaker.reset()

    async def start(self) -> None:
        """Start the Stomach polling loop."""
        self.pool = await asyncpg.create_pool(self.dsn)
        log.info("stomach_online", status="monitoring_peristalsis", interval=POLL_INTERVAL)

        while self._running:
            try:
                await self.poll_and_digest()
            except Exception as e:
                log.error("stomach_loop_error", error=str(e))
                self.breaker.record_failure()

            await asyncio.sleep(POLL_INTERVAL)

        await self.pool.close()


if __name__ == "__main__":
    stomach = Stomach(DB_DSN)
    try:
        asyncio.run(stomach.start())
    except KeyboardInterrupt:
        log.info("stomach_shutdown", reason="user_interrupt")
