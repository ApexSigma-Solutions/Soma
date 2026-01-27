"""
Memory tools for working memory, scratchpad, and promotion.
"""

from typing import Any, Dict, List, Optional
import httpx
import logging

from ..memory import get_redis_client
from ..config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# WORKING MEMORY & SCRATCHPAD (Redis)
# =============================================================================


async def scratch_write(
    session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Write a reasoning step to the scratchpad.

    Args:
        session_id: Current session identifier
        content: The reasoning thought or observation
        metadata: Optional metadata

    Returns:
        Entry ID
    """
    client = get_redis_client()
    return await client.scratch_write(session_id, content, metadata)


async def scratch_read(session_id: str, last_n: int = 10) -> List[Dict[str, Any]]:
    """
    Read recent reasoning trace from scratchpad.

    Args:
        session_id: Current session identifier
        last_n: Number of recent entries to return

    Returns:
        List of scratchpad entries
    """
    client = get_redis_client()
    return await client.scratch_read(session_id, last_n)


async def scratch_clear(session_id: str) -> str:
    """
    Clear the scratchpad for a session.

    Args:
        session_id: Current session identifier

    Returns:
        Status message
    """
    client = get_redis_client()
    count = await client.scratch_clear(session_id)
    return f"Cleared {count} entries from scratchpad"


async def set_working_memory(session_id: str, key: str, value: str) -> str:
    """
    Set a value in the session's working memory.

    Args:
        session_id: Current session identifier
        key: Context key
        value: Context value

    Returns:
        Confirmation message
    """
    client = get_redis_client()
    # Assuming value is string, but client handles complex types
    await client.set_working_memory(session_id, key, value)
    return f"Set working memory: {key}"


async def get_working_memory(session_id: str, key: Optional[str] = None) -> Any:
    """
    Retrieve working memory context.

    Args:
        session_id: Current session identifier
        key: Optional specific key to retrieve

    Returns:
        The requested value or full context object
    """
    client = get_redis_client()
    return await client.get_working_memory(session_id, key)


# =============================================================================
# MEMORY PROMOTION (Learning)
# =============================================================================


async def mark_significant(
    session_id: str, content: str, significance: float, reason: str
) -> str:
    """
    Mark an experience as significant for potential promotion.

    Store in pending list. If significance > threshold, may auto-promote.

    Args:
        session_id: Current session identifier
        content: The content to remember
        significance: 0.0 to 1.0 relevance score
        reason: Why this is significant

    Returns:
        Memory entry ID
    """
    # Validation
    if significance < 0.1:
        return f"Significance {significance} is too low. Memory ignored."

    client = get_redis_client()
    memory_id = await client.store_experience(
        session_id, content, significance, {"reason": reason}
    )

    # Auto-promote check
    if significance >= settings.memory_promotion_threshold:
        return await promote_memory(session_id, memory_id)

    return f"Stored as pending memory: {memory_id}"


async def promote_memory(session_id: str, memory_id: str) -> str:
    """
    Promote a pending memory to episodic storage (InGest-LLM).

    Sends the memory to InGest-LLM for embedding and storage in
    PostgreSQL/Neo4j.

    Args:
        session_id: Current session identifier
        memory_id: The ID of the pending memory

    Returns:
        Status message
    """
    client = get_redis_client()

    # 1. Retrieve pending memories
    pending = await client.get_pending_memories(session_id)
    memory = next((m for m in pending if m.id == memory_id), None)

    if not memory:
        return f"Error: Memory {memory_id} not found in pending list"

    # 2. Send to InGest-LLM
    try:
        # Retrieve recent scratchpad context
        scratchpad_context = await client.scratch_read(session_id, last_n=3)

        async with httpx.AsyncClient() as http:
            payload = {
                "source": "memos-mcp",
                "type": "working_experience",
                "content": memory.content,
                "metadata": {
                    "session_id": session_id,
                    "significance": memory.significance,
                    "original_metadata": memory.metadata,
                    "scratchpad_context": scratchpad_context,
                },
            }

            # Send to InGest-LLM behavior
            response = await http.post(
                f"{settings.ingest_llm_url}/ingest/experience",
                json=payload,
                timeout=settings.ingest_llm_timeout,
            )
            response.raise_for_status()

            # 3. Mark as promoted in Redis
            await client.mark_promoted(session_id, memory_id)

            return f"Successfully promoted memory {memory_id} to episodic storage"

    except Exception as e:
        logger.error(f"Failed to promote memory: {e}")
        return f"Error promoting memory: {str(e)}"
