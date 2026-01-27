"""
Redis client for memOS.MCP ephemeral memory.

Provides:
- Working memory: Current task context
- Scratchpad: Reasoning trace for agent work
- Pending memories: Awaiting promotion to episodic storage
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
import redis.asyncio as redis
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger(__name__)


class MemoryEntry(BaseModel):
    """A single memory entry."""

    id: str
    content: str
    significance: float = 0.0
    metadata: Dict[str, Any] = {}
    created_at: str
    source: str = "memos-mcp"


class PulseEvent(BaseModel):
    """A pulse stream event.

    Represents a user action captured in the real-time event stream.
    Events flow through: Pulse → Janitor → OmegaKG.
    """

    event_id: str  # Redis Stream ID (e.g., "1234567890-0")
    event_type: str  # "file_save", "terminal_cmd", "api_call", "consolidation"
    payload: Dict[str, Any]  # Event-specific data
    session_id: Optional[str] = None
    timestamp: datetime


class RedisMemoryClient:
    """
    Async Redis client for ephemeral memory operations.

    Key structure:
    - memos:{session}:working    - Hash: current context
    - memos:{session}:scratch    - List: reasoning trace
    - memos:{session}:pending    - List: memories awaiting promotion
    - pulse:stream               - Stream: real-time event feed (global)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
    ):
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._client: Optional[redis.Redis] = None
        self._prefix = "memos"

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is None:
            self._client = redis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {self._host}:{self._port}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Closed Redis connection")

    def _key(self, session_id: str, suffix: str) -> str:
        """Generate a Redis key."""
        return f"{self._prefix}:{session_id}:{suffix}"

    # =========================================================================
    # WORKING MEMORY
    # =========================================================================

    async def set_working_memory(
        self,
        session_id: str,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> None:
        """Set a value in working memory."""
        await self.connect()
        redis_key = self._key(session_id, "working")

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        await self._client.hset(redis_key, key, value)
        await self._client.expire(redis_key, ttl_seconds)
        logger.debug(f"Set working memory: {key}")

    async def get_working_memory(
        self,
        session_id: str,
        key: Optional[str] = None,
    ) -> Any:
        """Get value(s) from working memory."""
        await self.connect()
        redis_key = self._key(session_id, "working")

        if key:
            value = await self._client.hget(redis_key, key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        else:
            # Return all
            data = await self._client.hgetall(redis_key)
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except json.JSONDecodeError:
                    result[k] = v
            return result

    async def clear_working_memory(self, session_id: str) -> None:
        """Clear all working memory for session."""
        await self.connect()
        redis_key = self._key(session_id, "working")
        await self._client.delete(redis_key)
        logger.debug(f"Cleared working memory for session {session_id}")

    # =========================================================================
    # SCRATCHPAD
    # =========================================================================

    async def scratch_write(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Write to scratchpad (reasoning trace)."""
        await self.connect()
        redis_key = self._key(session_id, "scratch")

        entry = {
            "id": str(uuid4()),
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await self._client.rpush(redis_key, json.dumps(entry))
        await self._client.expire(redis_key, 7200)  # 2 hour TTL

        logger.debug(f"Wrote to scratchpad: {entry['id']}")
        return entry["id"]

    async def scratch_read(
        self,
        session_id: str,
        last_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Read scratchpad entries."""
        await self.connect()
        redis_key = self._key(session_id, "scratch")

        if last_n:
            entries = await self._client.lrange(redis_key, -last_n, -1)
        else:
            entries = await self._client.lrange(redis_key, 0, -1)

        return [json.loads(e) for e in entries]

    async def scratch_clear(self, session_id: str) -> int:
        """Clear scratchpad and return count of cleared entries."""
        await self.connect()
        redis_key = self._key(session_id, "scratch")

        count = await self._client.llen(redis_key)
        await self._client.delete(redis_key)

        logger.debug(f"Cleared {count} scratchpad entries for session {session_id}")
        return count

    # =========================================================================
    # PENDING MEMORIES (for promotion)
    # =========================================================================

    async def store_experience(
        self,
        session_id: str,
        content: str,
        significance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store an experience for potential promotion."""
        await self.connect()
        redis_key = self._key(session_id, "pending")

        entry = MemoryEntry(
            id=str(uuid4()),
            content=content,
            significance=significance,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        await self._client.rpush(redis_key, entry.model_dump_json())
        await self._client.expire(redis_key, 14400)  # 4 hour TTL

        logger.info(f"Stored experience {entry.id} (significance: {significance})")
        return entry.id

    async def get_pending_memories(
        self,
        session_id: str,
        min_significance: float = 0.0,
    ) -> List[MemoryEntry]:
        """Get pending memories, optionally filtered by significance."""
        await self.connect()
        redis_key = self._key(session_id, "pending")

        entries = await self._client.lrange(redis_key, 0, -1)
        memories = [MemoryEntry.model_validate_json(e) for e in entries]

        if min_significance > 0:
            memories = [m for m in memories if m.significance >= min_significance]

        return memories

    async def mark_promoted(self, session_id: str, memory_id: str) -> bool:
        """Mark a memory as promoted (remove from pending)."""
        await self.connect()
        redis_key = self._key(session_id, "pending")

        entries = await self._client.lrange(redis_key, 0, -1)
        for entry in entries:
            memory = MemoryEntry.model_validate_json(entry)
            if memory.id == memory_id:
                await self._client.lrem(redis_key, 1, entry)
                logger.info(f"Marked memory {memory_id} as promoted")
                return True

        return False

    # =========================================================================
    # UTILITY
    # =========================================================================

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        await self.connect()

        working_key = self._key(session_id, "working")
        scratch_key = self._key(session_id, "scratch")
        pending_key = self._key(session_id, "pending")

        return {
            "session_id": session_id,
            "working_memory_keys": await self._client.hlen(working_key),
            "scratch_entries": await self._client.llen(scratch_key),
            "pending_memories": await self._client.llen(pending_key),
        }

    # =========================================================================
    # PULSE STREAM (The Nervous System)
    # =========================================================================

    async def emit_pulse_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        stream_key: str = "pulse:stream",
        max_len: int = 1000,
    ) -> str:
        """Emit an event to the pulse stream.

        Args:
            event_type: Type of event ("file_save", "terminal_cmd", "api_call")
            payload: Event-specific data
            session_id: Optional session context
            stream_key: Redis stream key (default: "pulse:stream")
            max_len: Maximum stream length (MAXLEN ~max_len)

        Returns:
            str: Redis Stream ID (e.g., "1234567890-0")
        """
        await self.connect()

        event_data = {
            "event_type": event_type,
            "payload": json.dumps(payload),
            "session_id": session_id or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # XADD with MAXLEN ~max_len (approximate trimming for performance)
        stream_id = await self._client.xadd(
            stream_key,
            event_data,
            maxlen=max_len,
            approximate=True,  # Use ~ for better performance
        )

        logger.debug(f"Emitted pulse event {stream_id}: {event_type}")
        return stream_id

    async def read_pulse_stream(
        self,
        stream_key: str = "pulse:stream",
        last_id: str = "0-0",
        count: int = 10,
        block_ms: Optional[int] = None,
    ) -> List[PulseEvent]:
        """Read events from the pulse stream.

        Args:
            stream_key: Redis stream key
            last_id: Last seen stream ID ("0-0" for all, "$" for new only)
            count: Maximum number of events to read
            block_ms: Block for N milliseconds if no events (None = no blocking)

        Returns:
            List[PulseEvent]: Parsed pulse events
        """
        await self.connect()

        # XREAD [BLOCK ms] [COUNT n] STREAMS key last_id
        streams = {stream_key: last_id}

        if block_ms is not None:
            response = await self._client.xread(streams, count=count, block=block_ms)
        else:
            response = await self._client.xread(streams, count=count)

        # Parse response: [(stream_key, [(stream_id, {field: value}), ...])]
        events = []
        for stream_name, messages in response:
            for stream_id, data in messages:
                try:
                    events.append(
                        PulseEvent(
                            event_id=stream_id,
                            event_type=data["event_type"],
                            payload=json.loads(data["payload"]),
                            session_id=data.get("session_id") or None,
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse pulse event {stream_id}: {e}")

        return events

    async def trim_pulse_stream(
        self,
        stream_key: str = "pulse:stream",
        max_len: int = 1000,
    ) -> int:
        """Manually trim pulse stream to max length.

        Args:
            stream_key: Redis stream key
            max_len: Maximum stream length to retain

        Returns:
            int: Number of entries trimmed
        """
        await self.connect()

        # XTRIM stream MAXLEN ~ max_len
        trimmed = await self._client.xtrim(stream_key, maxlen=max_len, approximate=True)

        if trimmed > 0:
            logger.info(f"Trimmed {trimmed} entries from {stream_key}")

        return trimmed


# Global client instance
_redis_client: Optional[RedisMemoryClient] = None


def get_redis_client() -> RedisMemoryClient:
    """Get or create the global Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisMemoryClient(
            host=getattr(settings, "memos_redis_host", "localhost"),
            port=getattr(settings, "memos_redis_port", 6380),
            password=getattr(settings, "memos_redis_password", None),
        )
    return _redis_client
