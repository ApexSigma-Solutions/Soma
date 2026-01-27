import asyncio
import logging
import re

import asyncpg
import httpx

from ingest_llm_as.config import get_settings

logger = logging.getLogger(__name__)

# Matches LIN-123 or #123
ISSUE_PATTERN = re.compile(r"\b([A-Z]{2,5}-\d+)\b|\b#(\d+)\b")


class TerminalProcessor:
    """
    Workhorse service: Polls 'terminal_events' table, preps data,
    and proposes knowledge to the OmegaKG Guardian.
    """

    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self.db_url = self.settings.raw_db_url

    async def start(self):
        """Start the terminal processing loop."""
        self.running = True
        logger.info("Starting Terminal Processor (Workhorse) loop...")
        while self.running:
            try:
                processed_count = await self.process_pending_events()
                if processed_count == 0:
                    await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in terminal processor loop: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        self.running = False

    async def process_pending_events(self) -> int:
        """
        Fetch and process unprocessed terminal events.
        """
        db_url = self.settings.raw_db_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(db_url, timeout=30.0)

        try:
            rows = await conn.fetch("""
                SELECT id, command, cwd, exit_code, timestamp, session_id, host
                FROM terminal_events 
                WHERE processed = FALSE 
                LIMIT 10
            """)

            if not rows:
                return 0

            processed = 0
            for row in rows:
                try:
                    event_id = row["id"]
                    command = row["command"]

                    # 1. Prep Knowledge Digest
                    summary = f"Executed: {command} in {row['cwd']}"
                    entities = self._extract_references(command)

                    digest = {
                        "title": f"Terminal: {command[:30]}...",
                        "summary": summary,
                        "entities": [
                            {"name": e, "type": "Reference"} for e in entities
                        ],
                        "concepts": ["terminal-command"],
                        "decisions": [],
                        "outcomes": [f"Exit Code: {row['exit_code']}"],
                        "tags": ["terminal", "ghost"],
                    }

                    # 2. Commit to Guardian (OmegaKG)
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        guardian_url = "http://localhost:8765/guardian/commit"

                        payload = {
                            "raw_id": str(event_id),
                            "type": "terminal",
                            "digest": digest,
                            "metadata": {
                                "command": command,
                                "cwd": row["cwd"],
                                "exit_code": row["exit_code"],
                                "timestamp": row["timestamp"].isoformat()
                                if row["timestamp"]
                                else None,
                                "host": row["host"],
                            },
                        }

                        resp = await client.post(guardian_url, json=payload)
                        resp.raise_for_status()

                    # 3. Mark Processed
                    await conn.execute(
                        "UPDATE terminal_events SET processed = TRUE WHERE id = $1",
                        event_id,
                    )
                    processed += 1
                except Exception as e:
                    logger.error(f"Failed to process terminal event {row['id']}: {e}")

            return processed

        finally:
            await conn.close()

    def _extract_references(self, text: str):
        if not text:
            return []
        matches = ISSUE_PATTERN.findall(text)
        refs = []
        for m in matches:
            refs.extend([item for item in m if item])
        return list(set(refs))
