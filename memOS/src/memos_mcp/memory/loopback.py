"""Loopback Mechanism for memOS.

memOS is READ-ONLY for long-term memory (Neo4j/LanceDB).
To save memories, memOS must POST to InGest or OmegaKG Guardian.

This enforces the "Guardian-only-writer" constraint.
"""

from dataclasses import dataclass
from typing import Any
import logging
import httpx

logger = logging.getLogger(__name__)


@dataclass
class LoopbackConfig:
    """Configuration for the loopback mechanism."""

    ingest_url: str = "http://localhost:8766"
    guardian_url: str = "http://localhost:8765"
    timeout: float = 30.0


class MemoryLoopback:
    """Loopback client for saving memories via InGest or Guardian.

    memOS cannot write directly to Neo4j or LanceDB.
    All persistence must go through the proper channels.
    """

    def __init__(self, config: LoopbackConfig | None = None):
        self.config = config or LoopbackConfig()

    async def save_memory(
        self,
        content: str,
        entities: list[dict[str, str]] | None = None,
        tags: list[str] | None = None,
        source: str = "memos",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save a memory by POSTing to InGest.

        This queues the memory for processing by the Dagster pipeline
        (compression → indexing → Guardian commit).

        Args:
            content: The memory content to save
            entities: List of entities with 'name' and 'type'
            tags: Optional tags for categorization
            source: Source identifier
            metadata: Additional metadata

        Returns:
            Response from InGest API
        """
        payload = {
            "content": content,
            "entities": entities or [],
            "tags": tags or [],
            "source": source,
            "metadata": metadata or {},
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.post(
                    f"{self.config.ingest_url}/ingest/memory", json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(
                    f"Memory queued for ingestion: {result.get('id', 'unknown')}"
                )
                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"InGest returned error: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Failed to reach InGest: {e}")
                raise

    async def commit_directly(
        self,
        raw_id: str,
        content_type: str,
        title: str,
        summary: str,
        entities: list[dict[str, str]] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Commit directly to OmegaKG Guardian (bypass InGest).

        Use this for urgent or pre-processed memories that don't need
        the full Dagster pipeline.

        Args:
            raw_id: Unique identifier for the memory
            content_type: Type of content (e.g., 'memory_atom', 'conversation')
            title: Memory title
            summary: Memory summary/content
            entities: List of entities
            tags: Optional tags
            metadata: Additional metadata

        Returns:
            Response from Guardian API
        """
        payload = {
            "raw_id": raw_id,
            "type": content_type,
            "digest": {
                "title": title,
                "summary": summary,
                "entities": entities or [],
                "concepts": [],
                "decisions": [],
                "outcomes": [],
                "tags": tags or ["memos_loopback"],
            },
            "metadata": metadata or {"source": "memos_loopback"},
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.post(
                    f"{self.config.guardian_url}/guardian/commit", json=payload
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Memory committed to Guardian: {raw_id}")
                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"Guardian returned error: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Failed to reach Guardian: {e}")
                raise

    async def mark_significant(
        self,
        memory_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Mark a working memory as significant for promotion.

        This signals to InGest that the memory should be processed
        and stored in long-term memory.

        Args:
            memory_id: ID of the working memory to promote
            reason: Reason for marking as significant

        Returns:
            Response from InGest API
        """
        payload = {
            "memory_id": memory_id,
            "reason": reason,
            "action": "promote",
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.post(
                    f"{self.config.ingest_url}/ingest/promote", json=payload
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Promotion failed: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Failed to reach InGest: {e}")
                raise


# Global instance
_loopback: MemoryLoopback | None = None


def get_loopback() -> MemoryLoopback:
    """Get the global MemoryLoopback instance."""
    global _loopback
    if _loopback is None:
        _loopback = MemoryLoopback()
    return _loopback
