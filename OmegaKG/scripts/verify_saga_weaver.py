# Saga Verification Script
import asyncio
import logging
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from omega_kg.database import get_ingest_session, get_vector_session
from omega_kg.models.terminal import TerminalEvent, TerminalCommandData
from omega_kg.services.neo4j_adapter import Neo4jAdapter
from sqlalchemy import text
from datetime import datetime

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_saga")


async def inject_test_event():
    """Injects a terminal event that mimics a Saga action."""
    logger.info("💉 Injecting Test Event...")

    cmd_payload = TerminalCommandData(
        timestamp=datetime.now(),
        cwd="D:/projects/OmegaKG",
        command="echo 'Optimizing API response for LIN-777 and #42'",
        exit_code=0,
        session_id="verify-session-01",
        host="localhost",
    )

    async with get_ingest_session() as session:
        event = TerminalEvent(**cmd_payload.dict())
        session.add(event)
        await session.commit()
        await session.refresh(event)
        logger.info(f"✅ Event Injected. ID: {event.id}")
        return event.id


async def verify_processing(event_id):
    """Polls DB to check if the worker picked it up."""
    logger.info("⏳ Waiting for Worker to Process...")

    # Wait for up to 10 seconds (Worker poll is 5s)
    for _ in range(10):
        await asyncio.sleep(1)
        async with get_ingest_session() as session:
            event = await session.get(TerminalEvent, event_id)
            if event and event.processed:
                logger.info("✅ Event marked as PROCESSED.")
                return True

    logger.error("❌ Event was NOT processed. Is the embedding_worker running?")
    return False


async def verify_dual_write(event_id):
    """Checks Neo4j and PGVector for the Saga artifacts."""

    # 1. Check Neo4j
    logger.info("🔍 Verifying Neo4j (Structure)...")
    neo4j = Neo4jAdapter()
    try:
        query = "MATCH (t:TerminalExecution {id: $id})-[:RESOLVES_OR_RELATES]->(n) RETURN t, labels(n) as linked_labels"
        result = neo4j.run(query, {"id": str(event_id)})
        records = list(result)

        if records:
            logger.info(f"✅ Neo4j Node Found: {len(records)} relationships.")
        else:
            logger.warning("⚠️ Neo4j Node NOT found or no relationships linked.")
    finally:
        neo4j.close()

    # 2. Check PGVector (Memos)
    logger.info("🔍 Verifying PGVector (Recall)...")
    async with get_vector_session() as session:
        # Check for the specific event ID hash
        sql = text(
            "SELECT content, tags FROM memos.memories WHERE conversation_hash = :hash"
        )
        result = await session.execute(sql, {"hash": str(event_id)})
        row = result.fetchone()

        if row:
            logger.info("✅ Memory Found in PGVector.")
            logger.info(f"   Content Preview: {row[0][:50]}...")
            logger.info(f"   Tags: {row[1]}")
            if "#saga" in row[1]:
                logger.info("   ✅ '#saga' tag confirmed.")
        else:
            logger.error("❌ Memory NOT found in PGVector.")


async def main():
    print("--- SAGA WEAVER VERIFICATION ---")
    event_id = await inject_test_event()

    if await verify_processing(event_id):
        await verify_dual_write(event_id)
    else:
        print("Aborting verification due to processing failure.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
