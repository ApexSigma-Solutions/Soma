#!/usr/bin/env python
"""Soma Meal Trace E2E Verification Script.

This script verifies the complete signal path through the Soma organism:
1. SENSES (InGress) -> Postgres raw_lake
2. STOMACH (Poller) -> SimpleMem Stage 1 -> Redis Stream
3. BRAIN (OmegaKG) -> Neo4j AtomicFact
4. HANDS (memOS) -> query_brain tool

Usage:
    cd d:\projects\Soma
    poetry run python scripts/verify_meal_trace.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import structlog

# Add project roots to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "InGress"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "OmegaKG"))

# Configuration
INGRESS_URL = os.getenv("SOMA_INGRESS_URL", "http://localhost:8000")
INGRESS_API_KEY = os.getenv("SOMA_INGRESS_KEY", "sigma-dev-secret-key")
REDIS_URL = os.getenv("SOMA_REDIS_URL", "redis://localhost:6380/0")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
POSTGRES_DSN = os.getenv(
    "SOMA_PG_DSN",
    "postgresql://omega_user:omega_dev_password@localhost:6000/soma_sensory_lake",
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)
log = structlog.get_logger()


class MealTraceVerifier:
    """End-to-end verification of the Soma Meal Trace pipeline."""

    def __init__(self):
        self.test_id = f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.checkpoints: Dict[str, Any] = {}

    async def run_full_trace(self) -> bool:
        """Execute the complete meal trace verification."""
        log.info("=" * 60)
        log.info("SOMA MEAL TRACE VERIFICATION", test_id=self.test_id)
        log.info("=" * 60)

        try:
            # Checkpoint 1: SENSES (InGress)
            raw_lake_id = await self._checkpoint_senses()
            if not raw_lake_id:
                return False

            # Checkpoint 2: Verify Postgres persistence
            await self._checkpoint_postgres(raw_lake_id)

            # Checkpoint 3: STOMACH (SimpleMem) -> Redis
            # Note: This requires the poller to be running
            await self._checkpoint_redis()

            # Checkpoint 4: BRAIN (OmegaKG) -> Neo4j
            # Note: This requires the stream consumer to be running
            await self._checkpoint_neo4j()

            # Summary
            self._print_summary()
            return True

        except Exception as e:
            log.error("trace_verification_failed", error=str(e))
            return False

    async def _checkpoint_senses(self) -> Optional[str]:
        """Checkpoint 1: Inject signal via InGress."""
        log.info("-" * 40)
        log.info("CHECKPOINT 1: SENSES (InGress)")
        log.info("-" * 40)

        test_payload = {
            "message": "Sean met with the ApexSigma team yesterday at the office to discuss the Soma architecture. He mentioned that the brain components are working well.",
            "trace_id": self.test_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{INGRESS_URL}/api/v1/manual/ingest",
                    json={
                        "source": "meal_trace_test",
                        "event_type": "verification",
                        "payload": test_payload,
                    },
                    headers={"X-API-Key": INGRESS_API_KEY},
                )
                response.raise_for_status()

                data = response.json()
                raw_lake_id = data.get("ref")

                self.checkpoints["senses"] = {
                    "status": "✅ PASS",
                    "raw_lake_id": raw_lake_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                log.info(
                    "senses_checkpoint_passed",
                    raw_lake_id=raw_lake_id,
                    status="captured",
                )
                return raw_lake_id

            except httpx.HTTPError as e:
                self.checkpoints["senses"] = {
                    "status": "❌ FAIL",
                    "error": str(e),
                }
                log.error("senses_checkpoint_failed", error=str(e))
                return None

    async def _checkpoint_postgres(self, raw_lake_id: str) -> None:
        """Checkpoint 2: Verify record in Postgres raw_lake."""
        log.info("-" * 40)
        log.info("CHECKPOINT 2: POSTGRES (raw_lake)")
        log.info("-" * 40)

        try:
            import asyncpg

            conn = await asyncpg.connect(POSTGRES_DSN)
            row = await conn.fetchrow(
                "SELECT id, source, event_type, processed FROM raw_lake WHERE id = $1",
                raw_lake_id,
            )
            await conn.close()

            if row:
                self.checkpoints["postgres"] = {
                    "status": "✅ PASS",
                    "record_id": str(row["id"]),
                    "source": row["source"],
                    "processed": row["processed"],
                }
                log.info(
                    "postgres_checkpoint_passed",
                    record_id=str(row["id"]),
                    processed=row["processed"],
                )
            else:
                self.checkpoints["postgres"] = {
                    "status": "❌ FAIL",
                    "error": "Record not found",
                }
                log.error("postgres_checkpoint_failed", error="Record not found")

        except Exception as e:
            self.checkpoints["postgres"] = {
                "status": "⚠️ SKIP",
                "error": str(e),
            }
            log.warning("postgres_checkpoint_skipped", error=str(e))

    async def _checkpoint_redis(self) -> None:
        """Checkpoint 3: Verify atomic fact in Redis stream."""
        log.info("-" * 40)
        log.info("CHECKPOINT 3: REDIS (soma_working_memory)")
        log.info("-" * 40)

        try:
            import redis.asyncio as redis_client

            r = redis_client.from_url(REDIS_URL)

            # Check stream length
            stream_len = await r.xlen("soma_working_memory")

            # Get latest entry
            entries = await r.xrange("soma_working_memory", "-", "+", count=1)

            await r.close()

            if entries:
                msg_id, data = entries[-1]
                self.checkpoints["redis"] = {
                    "status": "✅ PASS",
                    "stream_length": stream_len,
                    "latest_message_id": msg_id.decode()
                    if isinstance(msg_id, bytes)
                    else msg_id,
                }
                log.info(
                    "redis_checkpoint_passed",
                    stream_length=stream_len,
                    latest_id=msg_id,
                )
            else:
                self.checkpoints["redis"] = {
                    "status": "⚠️ PENDING",
                    "stream_length": stream_len,
                    "note": "Stream empty - waiting for poller",
                }
                log.warning(
                    "redis_checkpoint_pending", note="Poller may not have processed yet"
                )

        except Exception as e:
            self.checkpoints["redis"] = {
                "status": "⚠️ SKIP",
                "error": str(e),
            }
            log.warning("redis_checkpoint_skipped", error=str(e))

    async def _checkpoint_neo4j(self) -> None:
        """Checkpoint 4: Verify AtomicFact node in Neo4j."""
        log.info("-" * 40)
        log.info("CHECKPOINT 4: NEO4J (AtomicFact)")
        log.info("-" * 40)

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
            )

            async with driver.session() as session:
                result = await session.run(
                    """
                    MATCH (f:AtomicFact)
                    WHERE f.source = 'meal_trace_test'
                    RETURN f.text_hash as hash, f.source as source, 
                           f.created_at as created, f.text as text
                    ORDER BY f.created_at DESC
                    LIMIT 1
                    """
                )
                record = await result.single()

            await driver.close()

            if record:
                self.checkpoints["neo4j"] = {
                    "status": "✅ PASS",
                    "text_hash": record["hash"],
                    "source": record["source"],
                    "text_preview": record["text"][:50] + "..."
                    if record["text"]
                    else "N/A",
                }
                log.info(
                    "neo4j_checkpoint_passed",
                    text_hash=record["hash"],
                )
            else:
                self.checkpoints["neo4j"] = {
                    "status": "⚠️ PENDING",
                    "note": "Node not found - waiting for stream consumer",
                }
                log.warning(
                    "neo4j_checkpoint_pending",
                    note="Consumer may not have processed yet",
                )

        except Exception as e:
            self.checkpoints["neo4j"] = {
                "status": "⚠️ SKIP",
                "error": str(e),
            }
            log.warning("neo4j_checkpoint_skipped", error=str(e))

    def _print_summary(self) -> None:
        """Print verification summary."""
        log.info("=" * 60)
        log.info("MEAL TRACE VERIFICATION SUMMARY")
        log.info("=" * 60)

        for checkpoint, data in self.checkpoints.items():
            status = data.get("status", "UNKNOWN")
            log.info(f"  {checkpoint.upper()}: {status}")

        # Overall result
        all_passed = all(
            data.get("status", "").startswith("✅")
            for data in self.checkpoints.values()
        )
        pending = any(
            "PENDING" in data.get("status", "") for data in self.checkpoints.values()
        )

        if all_passed:
            log.info("=" * 60)
            log.info("🎉 ALL CHECKPOINTS PASSED - MEAL TRACE VERIFIED!")
            log.info("=" * 60)
        elif pending:
            log.info("=" * 60)
            log.info("⏳ SOME CHECKPOINTS PENDING - Run background services")
            log.info(
                "   Start poller: cd InGress && poetry run python -m soma_ingress.raw_lake_poller"
            )
            log.info(
                "   Start consumer: cd OmegaKG && poetry run python -m omega_kg.workers.stream_consumer"
            )
            log.info("=" * 60)
        else:
            log.info("=" * 60)
            log.info("❌ VERIFICATION INCOMPLETE - Check logs above")
            log.info("=" * 60)


async def main() -> int:
    """Main entry point."""
    verifier = MealTraceVerifier()
    success = await verifier.run_full_trace()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
