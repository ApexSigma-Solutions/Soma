import asyncio
import logging
import json

import asyncpg
import httpx

from ingest_llm_as.config import get_settings
from ingest_llm_as.services.llm_summarizer import LLMSummarizer
from src.shared.pulse_emitter import get_pulse_emitter
import time

logger = logging.getLogger(__name__)


class ConversationIngestor:
    """
    Workhorse service: Polls 'raw_conversations' table, synthesizes content,
    and proposes knowledge to the OmegaKG Guardian.
    """

    def __init__(self):
        self.settings = get_settings()
        self.summarizer = LLMSummarizer()
        self.running = False
        self.pool = None

    async def start(self):
        """Start the ingestion loop."""
        self.running = True
        logger.info("Starting Conversation Ingestor (Workhorse) loop...")

        db_url = self.settings.raw_db_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )

        while self.running:
            # 1. Ensure DB Connection
            if not self.pool:
                try:
                    self.pool = await asyncpg.create_pool(
                        db_url, min_size=1, max_size=5
                    )
                    logger.info("Database connection pool established.")
                except Exception as e:
                    logger.error(f"Failed to create DB pool: {e}")
                    await asyncio.sleep(5)
                    continue

            # 2. Process
            try:
                processed_count = await self.process_pending_conversations()
                if processed_count == 0:
                    await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in ingestor loop: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def stop(self):
        self.running = False
        if hasattr(self, "pool") and self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed.")

    async def process_pending_conversations(self) -> int:
        """
        Fetch and process unprocessed conversations from raw_ingestions table.
        Filters for source_type='conversation' or similar conversation-related types.
        """
        if not self.pool:
            logger.error("Database pool not initialized!")
            return 0

        source_id = None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, ingestion_id, source_type, raw_payload, raw_metadata, captured_at
                    FROM raw_ingestions
                    WHERE processed = FALSE
                    AND source_type LIKE 'conversation%'
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                """)

                if not row:
                    return 0

                record_id = row["id"]
                source_id = str(
                    row.get("source_id", row.get("ingestion_id", "unknown"))
                )
                raw_data = json.loads(row["raw_payload"])
                raw_metadata = row.get("raw_metadata") or {}
                platform = raw_metadata.get("platform", "unknown")
                captured_at = row["captured_at"]

                logger.info(f"Processing conversation: {source_id}")
                start_time = time.perf_counter()

                try:
                    # 1. Summarize (Heavy Lifting)
                    messages = raw_data.get("messages", [])
                    summary_content = await self.summarizer.summarize_conversation(
                        messages, context=f"Platform: {platform}, Date: {captured_at}"
                    )

                    # 2. Prep Knowledge Digest
                    digest = {
                        "title": f"Conversation: {source_id[:8]}",
                        "summary": summary_content,
                        "entities": [],  # In future, extract entities with LLM
                        "concepts": [],
                        "decisions": [],
                        "outcomes": [],
                        "tags": ["ai-conversation", platform.lower()],
                    }

                    # 3. Commit to Guardian (OmegaKG)
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        # Assuming OmegaKG is at http://localhost:8765
                        guardian_url = "http://localhost:8765/guardian/commit"
                        logger.debug(
                            f"Committing knowledge to Guardian: {guardian_url}"
                        )

                        payload = {
                            "raw_id": str(record_id),
                            "type": "conversation",
                            "digest": digest,
                            "metadata": {
                                "platform": platform,
                                "source_id": source_id,
                                "captured_at": captured_at.isoformat(),
                            },
                        }

                        resp = await client.post(guardian_url, json=payload)
                        resp.raise_for_status()
                        commit_result = resp.json()
                        logger.debug(f"Guardian result: {commit_result.get('message')}")

                    # 4. Update Record (Mark Processed)
                    await conn.execute(
                        """
                        UPDATE raw_ingestions
                        SET processed = TRUE,
                        processed_at = NOW(),
                        last_error = NULL
                        WHERE id = $1
                    """,
                        record_id,
                    )

                    # Emit Pulse
                    try:
                        duration = time.perf_counter() - start_time
                        pulse = get_pulse_emitter()
                        pulse.emit(
                            event_type="conversation_processed",
                            content=f"Processed conversation {source_id} ({duration:.2f}s)",
                            metadata={
                                "source_id": source_id,
                                "platform": platform,
                                "duration_seconds": round(duration, 3),
                                "model": "LLMSummarizer",
                            },
                        )
                    except Exception as pe:
                        logger.warning(f"Pulse emit failed: {pe}")

                    logger.info(f"Successfully processed {source_id} via Guardian.")
                    return 1

                except Exception as processing_error:
                    logger.error(f"Failed to process {source_id}: {processing_error}")
                    # Mark as failed in DB to prevent infinite loop
                    await conn.execute(
                        """
                        UPDATE raw_ingestions
                        SET processed = TRUE,
                        processed_at = NOW(),
                        last_error = $2
                        WHERE id = $1
                        """,
                        record_id,
                        str(processing_error),
                    )
                    return 1  # We moved past this item

        except Exception as e:
            if source_id:
                logger.error(f"Failed to process {source_id}: {e}", exc_info=True)
            else:
                logger.error(
                    f"Failed to fetch conversation for processing: {e}", exc_info=True
                )
            return 0
