"""
Pulse Emitter - Nervous System Signaling for InGest-LLM

This module provides the PulseEmitter class for sending real-time events
to memOS via Redis Streams when file processing completes.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import redis

from ingest_llm_as.config import get_settings

logger = logging.getLogger(__name__)


class PulseEmitter:
    """
    Emits system events to Redis Streams for the Nervous System.

    This class enables InGest-LLM to notify memOS of job completion events
    via Redis Streams, implementing the "Gastric Signaling" requirement
    of the Phase 3.5 Nervous System - System Symbiosis.
    """

    _instance: Optional["PulseEmitter"] = None

    def __init__(self, host: str = "localhost", port: int = 6380):
        """
        Initialize the Pulse Emitter.

        Args:
            host: Redis host (default: localhost)
            port: Redis port (default: 6380 for Pulse instance)
        """
        self.host = host
        self.port = port
        self._client: Optional[redis.Redis] = None
        self._stream_key = "pulse:stream"

    def _get_client(self) -> redis.Redis:
        """Get or create Redis client connection."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            logger.info(f"PulseEmitter connected to Redis at {self.host}:{self.port}")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if Redis connection is available."""
        try:
            client = self._get_client()
            client.ping()
            return True
        except redis.ConnectionError:
            return False

    def emit(
        self,
        event_type: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Emit an event to the pulse stream.

        Args:
            event_type: Type of event (e.g., "digestion_complete")
            content: Human-readable content/message about the event
            metadata: Optional dictionary containing event metadata

        Returns:
            The message ID if successful, None otherwise
        """
        try:
            client = self._get_client()

            # Build the event payload
            event_data = {
                "event_type": event_type,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": json.dumps(metadata or {}),
            }

            # Use XADD to publish to the stream
            message_id = client.xadd(self._stream_key, event_data)

            logger.info(
                f"Pulse emitted: event_type={event_type}, message_id={message_id}"
            )

            return message_id

        except redis.RedisError as e:
            logger.error(f"Failed to emit pulse event: {e}")
            return None

    def emit_digestion_complete(
        self,
        filename: str,
        duration_seconds: float,
        ram_percent: float,
        model: str,
        chunk_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Optional[str]:
        """
        Emit a 'digestion_complete' event when file processing finishes.

        This is the primary integration point called from graph_parser.py
        after FileLoaderService processes a file.

        Args:
            filename: Name of the processed file
            duration_seconds: Processing time in seconds
            ram_percent: RAM usage during processing
            model: Embedding/LLM model used
            chunk_count: Number of chunks processed (optional)
            error: Error message if processing failed (optional)

        Returns:
            The message ID if successful, None otherwise
        """
        metadata = {
            "filename": filename,
            "duration_seconds": round(duration_seconds, 3),
            "ram_percent": round(ram_percent, 1),
            "model": model,
        }

        if chunk_count is not None:
            metadata["chunk_count"] = chunk_count

        if error:
            metadata["error"] = error
            content = f"Digestion failed: {filename} - {error}"
        else:
            content = f"Digestion complete: {filename} ({duration_seconds:.2f}s, {chunk_count or 'N/A'} chunks)"

        return self.emit(
            event_type="digestion_complete",
            content=content,
            metadata=metadata,
        )

    def close(self):
        """Close the Redis connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("PulseEmitter connection closed")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

    @classmethod
    def get_instance(cls) -> "PulseEmitter":
        """
        Get singleton instance of PulseEmitter.

        Returns:
            PulseEmitter instance configured from settings
        """
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(
                host=settings.redis_host,
                port=settings.redis_port,
            )
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)."""
        if cls._instance:
            cls._instance.close()
        cls._instance = None


# Convenience function for quick access
def get_pulse_emitter() -> PulseEmitter:
    """Get the global PulseEmitter instance."""
    return PulseEmitter.get_instance()
