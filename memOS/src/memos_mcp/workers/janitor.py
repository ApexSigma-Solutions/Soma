"""
Janitor background worker for memOS.MCP Pulse system.

The Janitor watches the pulse stream and consolidates significant
event clusters into knowledge digests for OmegaKG.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

import httpx
from pydantic import BaseModel

from ..memory import get_redis_client, PulseEvent

logger = logging.getLogger(__name__)


class ConsolidationThresholds(BaseModel):
    """Thresholds for triggering event consolidation."""

    buffer_size: int = 10  # Events before consolidation
    timeout_seconds: int = 300  # Time since last consolidation
    error_immediate: bool = True  # Consolidate immediately on error events


class KnowledgeDigestPayload(BaseModel):
    """Simplified knowledge digest for OmegaKG validation API."""

    source_id: str
    digest_type: str = "terminal_event"
    title: str
    content: str
    summary: Optional[str] = None
    embedding: List[float]
    metadata: Dict[str, Any] = {}
    tags: List[str] = []
    references: Dict[str, List[str]] = {}
    captured_at: datetime
    processed_at: datetime


class JanitorWorker:
    """Background worker for pulse stream consolidation.

    Responsibilities:
    1. Watch Redis pulse stream via XREAD
    2. Buffer events in memory
    3. Apply threshold logic (count, time, significance)
    4. Consolidate events into knowledge digests
    5. Submit digests to OmegaKG validation API
    6. Handle graceful shutdown
    """

    def __init__(
        self,
        stream_key: str = "pulse:stream",
        thresholds: Optional[ConsolidationThresholds] = None,
        omegakg_url: str = "http://localhost:8765/api/validate",
    ):
        self.stream_key = stream_key
        self.thresholds = thresholds or ConsolidationThresholds()
        self.omegakg_url = omegakg_url

        self.redis_client = get_redis_client()
        self.event_buffer: List[PulseEvent] = []
        self.last_consolidation: Optional[datetime] = None
        self.last_stream_id: str = "$"  # Start from new events only

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the Janitor worker."""
        if self._running:
            logger.warning("Janitor already running")
            return

        logger.info(f"Starting Janitor worker (stream: {self.stream_key})")
        self._running = True
        self._task = asyncio.create_task(self._process_stream())

        # Register signal handlers for graceful shutdown (Unix only)
        # Windows doesn't support asyncio signal handlers
        if sys.platform != "win32":
            try:
                import signal

                loop = asyncio.get_event_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(
                        sig, lambda: asyncio.create_task(self.stop())
                    )
                logger.debug("Signal handlers registered (Unix platform)")
            except (NotImplementedError, AttributeError):
                # Windows or other platforms that don't support signal handlers
                # Graceful shutdown will still work via lifespan context manager
                logger.debug("Signal handlers not available on this platform")
        else:
            logger.debug("Signal handlers skipped on Windows")

    async def stop(self) -> None:
        """Stop the Janitor worker gracefully."""
        if not self._running:
            return

        logger.info("Stopping Janitor worker (flushing buffer)")
        self._running = False

        # Flush remaining events
        if self.event_buffer:
            await self._consolidate_events(force=True)

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Janitor worker stopped")

    async def _process_stream(self) -> None:
        """Main event processing loop."""
        logger.info("[Janitor] Connecting to Redis...")
        await self.redis_client.connect()
        logger.info("[Janitor] Connected to Redis. Starting loop.")

        while self._running:
            try:
                # logger.info(f"[Janitor] Reading stream {self.stream_key} (last_id={self.last_stream_id})")
                # Read from stream (Non-blocking to avoid Windows Proactor crash)
                events = await self.redis_client.read_pulse_stream(
                    stream_key=self.stream_key,
                    last_id=self.last_stream_id,
                    count=10,
                    block_ms=None,
                )

                if events:
                    logger.info(f"[Janitor] Received {len(events)} events")
                    for event in events:
                        await self._handle_event(event)
                        self.last_stream_id = event.event_id
                else:
                    # No events, sleep 1s to prevent CPU spin
                    await asyncio.sleep(1)

                # Check timeout-based consolidation
                await self._check_timeout()

            except asyncio.CancelledError:
                logger.info("Janitor stream processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing pulse stream: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error

    async def _handle_event(self, event: PulseEvent) -> None:
        """Handle a single pulse event."""
        logger.debug(f"Received event: {event.event_type} ({event.event_id})")

        self.event_buffer.append(event)

        # Check count-based threshold
        if len(self.event_buffer) >= self.thresholds.buffer_size:
            logger.info(f"Buffer threshold reached ({len(self.event_buffer)} events)")
            await self._consolidate_events()

        # Check significance-based threshold (error events)
        elif self.thresholds.error_immediate and event.event_type == "error":
            logger.warning("Error event detected, consolidating immediately")
            await self._consolidate_events()

    async def _check_timeout(self) -> None:
        """Check if timeout threshold has been exceeded."""
        if not self.event_buffer or not self.last_consolidation:
            return

        elapsed = (datetime.now(timezone.utc) - self.last_consolidation).total_seconds()

        if elapsed >= self.thresholds.timeout_seconds:
            logger.info(f"Timeout threshold reached ({elapsed:.0f}s)")
            await self._consolidate_events()

    async def _consolidate_events(self, force: bool = False) -> None:
        """Consolidate buffered events into a knowledge digest."""
        if not self.event_buffer:
            return

        event_count = len(self.event_buffer)
        logger.info(f"Consolidating {event_count} events (force={force})")

        try:
            # Create knowledge digest
            digest = await self._create_digest(self.event_buffer)

            # Submit to OmegaKG
            await self._submit_to_omegakg(digest)

            # Also emit consolidation event to stream for dashboard visibility
            await self.redis_client.emit_pulse_event(
                event_type="consolidation",
                payload={
                    "event_count": event_count,
                    "digest_id": digest.source_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                stream_key=self.stream_key,
            )

            # Clear buffer
            self.event_buffer.clear()
            self.last_consolidation = datetime.now(timezone.utc)

            logger.info(f"Successfully consolidated {event_count} events")

        except Exception as e:
            logger.error(f"Failed to consolidate events: {e}", exc_info=True)
            # TODO: Implement dead-letter queue for failed consolidations

    async def _create_digest(self, events: List[PulseEvent]) -> KnowledgeDigestPayload:
        """Create a knowledge digest from buffered events."""
        # Generate unique source ID
        source_id = f"pulse_{uuid4().hex[:12]}"

        # Concatenate event details
        content_lines = []
        for event in events:
            timestamp = event.timestamp.strftime("%H:%M:%S")
            payload_str = str(event.payload)
            content_lines.append(f"[{timestamp}] {event.event_type}: {payload_str}")

        content = "\n".join(content_lines)

        # Create title
        event_types = ", ".join(set(e.event_type for e in events))
        title = f"Pulse Cluster: {len(events)} events ({event_types})"

        # TODO: Generate summary using LLM
        summary = f"Consolidated {len(events)} pulse events"

        # TODO: Generate embedding using Ollama
        # For now, use placeholder (zeros)
        embedding = [0.0] * 1024

        # Extract metadata
        metadata = {
            "event_count": len(events),
            "event_types": list(set(e.event_type for e in events)),
            "session_ids": list(set(e.session_id for e in events if e.session_id)),
            "time_span": {
                "start": min(e.timestamp for e in events).isoformat(),
                "end": max(e.timestamp for e in events).isoformat(),
            },
        }

        return KnowledgeDigestPayload(
            source_id=source_id,
            title=title,
            content=content,
            summary=summary,
            embedding=embedding,
            metadata=metadata,
            tags=["pulse", "automated"],
            captured_at=min(e.timestamp for e in events),
            processed_at=datetime.now(timezone.utc),
        )

    async def _submit_to_omegakg(self, digest: KnowledgeDigestPayload) -> None:
        """Submit knowledge digest to OmegaKG validation API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.omegakg_url,
                json=digest.model_dump(mode="json"),
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                f"Submitted digest {digest.source_id} to OmegaKG: "
                f"{result.get('status', 'unknown')}"
            )
