"""
Event Processor Worker (TN-103)

Asynchronous event processor that polls for unprocessed webhook events
and routes them to appropriate domain handlers.

Design Pattern: Producer-Consumer with Database as Queue
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.database.session import AsyncSessionLocal
from omega_kg.domain.linear.processor import get_linear_processor
from omega_kg.models.webhook import RawWebhookEvent
from omega_kg.settings import settings

logger = logging.getLogger(__name__)


class EventProcessorMetrics:
    """Track event processor metrics for monitoring and observability."""

    def __init__(self) -> None:
        """Initialize metrics with zero values."""
        self.processed_count = 0
        self.error_count = 0
        self.batch_count = 0
        self.last_batch_time = 0.0
        self.start_time = time.time()

    def record_processed(self) -> None:
        """Record successful processing of an event."""
        self.processed_count += 1

    def record_error(self) -> None:
        """Record a processing error."""
        self.error_count += 1

    def record_batch(self, duration: float) -> None:
        """Record batch processing completion."""
        self.batch_count += 1
        self.last_batch_time = duration

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics as a dictionary."""
        uptime = time.time() - self.start_time
        return {
            "processed_total": self.processed_count,
            "errors_total": self.error_count,
            "batches_total": self.batch_count,
            "last_batch_duration": self.last_batch_time,
            "uptime_seconds": uptime,
            "processing_rate": self.processed_count / uptime if uptime > 0 else 0,
        }

    def log_metrics(self) -> None:
        """Log current metrics to application logs."""
        stats = self.get_stats()
        logger.info(
            f"EventProcessor metrics: "
            f"processed={stats['processed_total']}, "
            f"errors={stats['errors_total']}, "
            f"batches={stats['batches_total']}, "
            f"rate={stats['processing_rate']:.2f}/s"
        )


class EventProcessor:
    """
    Asynchronous event processor for webhook events.

    Polls the database for unprocessed events, routes them to
    appropriate handlers based on source, and updates processing status.

    Attributes:
        running: Flag indicating if processor is active
        metrics: EventProcessorMetrics instance for tracking
        handlers: Dictionary mapping sources to handler functions
        linear_processor: LinearProcessor instance for Linear events
    """

    def __init__(self) -> None:
        """Initialize event processor with handlers."""
        self.running = False
        self.metrics = EventProcessorMetrics()

        # Handler registry - maps event sources to handler functions
        self.handlers: Dict[str, Callable] = {
            "linear": self._handle_linear_event,
            # Future: 'github': self._handle_github_event,
            # Future: 'gitlab': self._handle_gitlab_event,
        }

        # Get singleton Linear processor instance
        self.linear_processor = get_linear_processor()

    async def start(self) -> None:
        """
        Start the infinite polling loop.

        Main entry point for the event processor. Runs until
        self.running is set to False via stop() method.
        """
        self.running = True
        logger.info("Event Processor started")

        while self.running:
            try:
                processed_count = await self.process_batch()

                # Adaptive sleep: shorter if we processed events, longer if idle
                if processed_count > 0:
                    await asyncio.sleep(0.1)  # Quick retry when work exists
                else:
                    await asyncio.sleep(settings.webhook_poll_interval)

            except Exception as e:
                logger.error(f"Polling loop error: {e}", exc_info=True)
                await asyncio.sleep(5.0)  # Backoff on crash

    async def stop(self) -> None:
        """
        Stop processor gracefully.

        Sets running flag to False. The loop will exit on next iteration.
        In-flight processing completes before shutdown.
        """
        logger.info("Stopping EventProcessor...")
        self.running = False
        # Loop will exit on next iteration
        # No need to wait for tasks as they complete within the loop

    async def process_batch(self) -> int:
        """
        Process a batch of pending events.

        Fetches unprocessed events from database, routes them to handlers,
        and updates their processing status.

        Returns:
            int: Number of events processed in this batch
        """
        batch_start = time.time()

        async with AsyncSessionLocal() as session:
            try:
                events = await self._fetch_pending(session)

                if not events:
                    return 0

                processed_count = 0
                for event in events:
                    try:
                        payload = self._parse_payload(event.payload)
                        success = await self._dispatch(event, payload)

                        if success:
                            await self._mark_complete(session, event)
                        else:
                            await self._mark_failed(
                                session, event, "Handler returned False"
                            )

                        processed_count += 1

                    except Exception as e:
                        await self._mark_failed(session, event, str(e))
                        processed_count += 1

                self.metrics.record_batch(time.time() - batch_start)

                # Log metrics every 10 batches
                if self.metrics.batch_count % 10 == 0:
                    self.metrics.log_metrics()

                return processed_count

            except Exception as e:
                await session.rollback()
                logger.error(f"Batch processing failed: {e}", exc_info=True)
                return 0

    async def _fetch_pending(self, session: AsyncSession) -> List[RawWebhookEvent]:
        """
        Fetch pending events with row-level locking.

        Uses with_for_update(skip_locked=True) to prevent concurrent
        processing of the same events by multiple workers.

        Args:
            session: SQLAlchemy async session

        Returns:
            List of unprocessed RawWebhookEvent objects
        """
        query = (
            select(RawWebhookEvent)
            .where(RawWebhookEvent.processed_status == False)  # noqa: E712
            .order_by(RawWebhookEvent.received_at)
            .limit(settings.webhook_batch_size)
            .with_for_update(skip_locked=True)  # Prevent concurrent processing
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def _dispatch(self, event: RawWebhookEvent, payload: Dict[str, Any]) -> bool:
        """
        Route event to appropriate handler.

        Looks up handler based on event.source and executes it.

        Args:
            event: The RawWebhookEvent to process
            payload: Parsed JSON payload dictionary

        Returns:
            bool: True if processed successfully, False otherwise
        """
        handler = self.handlers.get(event.source)

        if not handler:
            logger.warning(f"Unknown event source: {event.source}")
            return False

        try:
            return await handler(event, payload)
        except Exception as e:
            logger.error(f"Handler error for {event.source}: {e}", exc_info=True)
            return False

    async def _handle_linear_event(
        self, event: RawWebhookEvent, payload: Dict[str, Any]
    ) -> bool:
        """
        Process Linear webhook event.

        Delegates to LinearProcessor for domain logic.

        Args:
            event: The RawWebhookEvent to process
            payload: Parsed JSON payload dictionary

        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Extract event type for routing
            event_type = payload.get("type", "unknown")
            action = payload.get("action", "unknown")

            logger.info(f"Processing Linear event: {event_type}.{action}")

            # Call domain processor
            success = await self.linear_processor.process_single_event(payload)

            if success:
                self.metrics.record_processed()
            else:
                self.metrics.record_error()

            return success

        except Exception as e:
            logger.error(f"Linear handler error: {e}", exc_info=True)
            self.metrics.record_error()
            return False

    def _parse_payload(self, payload: Any) -> Dict[str, Any]:
        """
        Parse payload from database format.

        Handles both bytes and string payloads from database.

        Args:
            payload: Raw payload from database (bytes or str)

        Returns:
            Parsed JSON dictionary
        """
        import json

        # Decode bytes to string for parsing
        if isinstance(payload, bytes):
            payload_str = payload.decode("utf-8")
        else:
            payload_str = payload

        try:
            return json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse payload as JSON: {e}")
            return {}

    async def _mark_complete(
        self, session: AsyncSession, event: RawWebhookEvent
    ) -> None:
        """
        Mark event as successfully processed.

        Args:
            session: SQLAlchemy async session
            event: The RawWebhookEvent to mark complete
        """
        event.processed_status = True
        event.error_log = None
        await session.commit()

    async def _mark_failed(
        self, session: AsyncSession, event: RawWebhookEvent, error: str
    ) -> None:
        """
        Mark event as failed with error details.

        Args:
            session: SQLAlchemy async session
            event: The RawWebhookEvent to mark failed
            error: Error message to log
        """
        event.processed_status = True  # Mark as processed to prevent retry loop
        event.error_log = error[:1000]  # Truncate to prevent oversized logs
        await session.commit()
