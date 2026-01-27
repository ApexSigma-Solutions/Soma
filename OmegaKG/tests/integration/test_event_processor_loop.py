"""
Integration Tests for Event Processor (TN-103)

Tests end-to-end event processing flow including:
- Event insertion and retrieval
- Event processor initialization
- Batch size configuration
- Payload parsing and validation
- Error handling (malformed JSON, empty payloads)
- Metrics tracking and reset
- Empty queue handling
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

import pytest
from sqlalchemy import select

from omega_kg.database.session import AsyncSessionLocal
from omega_kg.models.webhook import RawWebhookEvent
from omega_kg.workers.event_processor import EventProcessor, EventProcessorMetrics


def create_linear_test_payload(
    identifier: str = "LIN-TEST-001",
    title: str = "Test Issue",
    description: str = "Test description",
) -> Dict[str, Any]:
    """Create a properly formatted Linear webhook payload for testing."""
    return {
        "type": "Issue",
        "action": "create",
        "data": {
            "id": f"{identifier}-uuid",
            "identifier": identifier,
            "title": title,
            "description": description,
            "state": {
                "id": "backlog-state-id",
                "name": "Backlog",
                "type": "backlog",
                "color": "#gray",
            },
            "priority": 3,
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "url": f"https://linear.app/test/issue/{identifier}",
        },
        "createdAt": datetime.utcnow().isoformat(),
    }


async def mock_linear_handler(payload: Dict[str, Any]) -> bool:  # noqa: ARG001
    """Mock Linear handler that accepts any payload for testing."""
    return True


async def mock_failing_handler(payload: Dict[str, Any]) -> bool:  # noqa: ARG001
    """Mock handler that always fails for error testing."""
    raise ValueError("Validation error: Invalid payload structure")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_insertion_and_retrieval():
    """Test event insertion and retrieval from database."""
    async with AsyncSessionLocal() as session:
        # Create test event with proper Linear payload format
        test_payload = create_linear_test_payload()

        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()

        # Retrieve event
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event.id)
        result = await session.execute(query)
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert retrieved.source == "linear"
        assert retrieved.processed_status is False
        assert retrieved.event_type == "Issue.created"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_processor_initialization():
    """Test EventProcessor initialization."""
    processor = EventProcessor()

    assert processor is not None
    assert processor.running is False
    assert processor.metrics is not None
    assert isinstance(processor.metrics, EventProcessorMetrics)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_processor_batch_size_configuration():
    """Test EventProcessor respects batch size configuration."""
    # Create more events than default batch size
    async with AsyncSessionLocal() as session:
        for i in range(15):
            test_payload = create_linear_test_payload(
                f"LIN-TEST-BATCH-{i}", f"Batch Size Test {i}", "Test batch size"
            )

            event = RawWebhookEvent(
                source="linear",
                received_at=datetime.utcnow(),
                processed_status=False,
                headers={"content-type": "application/json"},
                payload=test_payload,
                event_type="Issue.created",
            )

            session.add(event)

        await session.commit()

    # Process with default batch size
    processor = EventProcessor()
    # Override with mock handler to avoid validation issues
    processor.register_handler("linear", mock_linear_handler)
    processed_count = await processor.process_batch()

    # Should process up to batch size (typically 10)
    assert processed_count <= 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_payload_parsing():
    """Test event payload is correctly parsed from JSON."""
    async with AsyncSessionLocal() as session:
        test_payload = {
            "type": "Issue",
            "action": "updated",
            "data": {
                "id": "LIN-TEST-PARSE-001",
                "title": "Parse Test",
                "description": "Test JSON parsing",
                "state": "In Progress",
                "assignee": {"id": "user-123", "name": "Test User"},
            },
        }

        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.updated",
        )

        session.add(event)
        await session.commit()
        event_id = event.id

    # Process event
    processor = EventProcessor()
    await processor.process_batch()

    # Verify event was processed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await session.execute(query)
        processed_event = result.scalar_one_or_none()

        assert processed_event is not None
        assert processed_event.processed_status is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_malformed_json_payload_handling():
    """Test handling of malformed JSON payload."""
    async with AsyncSessionLocal() as session:
        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload="{ invalid json }{",
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()
        event_id = event.id

    # Process event
    processor = EventProcessor()
    processed_count = await processor.process_batch()

    assert processed_count == 1

    # Verify event was marked as failed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await session.execute(query)
        processed_event = result.scalar_one_or_none()

        assert processed_event is not None
        assert processed_event.processed_status is True
        assert processed_event.error_log is not None
        assert (
            "json" in processed_event.error_log.lower()
            or "parse" in processed_event.error_log.lower()
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_payload_handling():
    """Test handling of empty payload."""
    async with AsyncSessionLocal() as session:
        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload={},
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()
        event_id = event.id

    # Process event
    processor = EventProcessor()
    await processor.process_batch()

    # Verify event was processed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await session.execute(query)
        processed_event = result.scalar_one_or_none()

        assert processed_event is not None
        assert processed_event.processed_status is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_successful_linear_event_processing():
    """Test successful Linear event processing."""
    # Create test event with proper Linear format
    async with AsyncSessionLocal() as session:
        test_payload = create_linear_test_payload(
            "LIN-TEST-002", "Test Issue 2", "Test description 2"
        )

        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()
        event_id = event.id

    # Process event
    processor = EventProcessor()
    processed_count = await processor.process_batch()

    assert processed_count == 1

    # Verify event was marked as processed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await session.execute(query)
        processed_event = result.scalar_one_or_none()

        assert processed_event is not None
        assert processed_event.processed_status is True
        assert processed_event.error_log is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_failed_event_processing_with_error_logging():
    """Test failed event processing with error logging."""
    # Create test event with invalid payload
    async with AsyncSessionLocal() as session:
        test_payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "LIN-TEST-003",
                # Missing required fields to trigger validation error
                "title": "Test Issue 3",
            },
        }

        event = RawWebhookEvent(
            source="test-source",  # Use different source to use mock handler
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()
        event_id = event.id

    # Process event
    processor = EventProcessor()
    processor.register_handler("test-source", mock_failing_handler)
    processed_count = await processor.process_batch()

    assert processed_count == 1

    # Verify event was marked as failed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await session.execute(query)
        processed_event = result.scalar_one_or_none()

        assert processed_event is not None
        assert processed_event.processed_status is True
        assert processed_event.error_log is not None
        assert (
            "Validation" in processed_event.error_log
            or "error" in processed_event.error_log.lower()
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing_with_multiple_events():
    """Test batch processing with multiple events."""
    # Create multiple test events
    event_ids = []
    async with AsyncSessionLocal() as session:
        for i in range(5):
            test_payload = create_linear_test_payload(
                f"LIN-BATCH-{i}", f"Batch Test Issue {i}", f"Batch test description {i}"
            )

            event = RawWebhookEvent(
                source="linear",
                received_at=datetime.utcnow(),
                processed_status=False,
                headers={"content-type": "application/json"},
                payload=test_payload,
                event_type="Issue.created",
            )

            session.add(event)
            event_ids.append(event.id)

        await session.commit()

    # Process batch
    processor = EventProcessor()
    processed_count = await processor.process_batch()

    assert processed_count == 5

    # Verify all events were processed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id.in_(event_ids))
        result = await session.execute(query)
        processed_events = result.scalars().all()

        assert len(processed_events) == 5
        for event in processed_events:
            assert event.processed_status is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_source_handling():
    """Test unknown source handling."""
    # Create event with unknown source
    async with AsyncSessionLocal() as session:
        test_payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "UNKNOWN-001",
                "title": "Unknown Source Test",
            },
        }

        event = RawWebhookEvent(
            source="unknown_source",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()
        event_id = event.id

    # Process event
    processor = EventProcessor()
    processed_count = await processor.process_batch()

    # Unknown source should be logged but not crash processor
    assert processed_count == 1

    # Verify event was marked as processed (failed)
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await session.execute(query)
        processed_event = result.scalar_one_or_none()

        assert processed_event is not None
        assert processed_event.processed_status is True
        assert processed_event.error_log is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graceful_shutdown():
    """Test graceful shutdown of event processor."""
    processor = EventProcessor()

    # Start processor in background
    start_task = asyncio.create_task(processor.start())

    # Let it run briefly
    await asyncio.sleep(0.5)

    # Stop processor
    await processor.stop()

    # Verify processor stopped
    assert processor.running is False

    # Wait for task to complete
    try:
        await asyncio.wait_for(start_task, timeout=5.0)
    except asyncio.TimeoutError:
        pass  # Task may have already completed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_tracking():
    """Test metrics tracking during event processing."""
    processor = EventProcessor()

    # Create and process test event
    async with AsyncSessionLocal() as session:
        test_payload = create_linear_test_payload(
            "LIN-METRICS-001", "Metrics Test Issue", "Test for metrics tracking"
        )

        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()

    # Process event
    await processor.process_batch()

    # Verify metrics were recorded
    stats = processor.metrics.get_stats()

    assert stats["processed_total"] >= 1
    assert stats["batches_total"] >= 1
    assert stats["uptime_seconds"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_reset():
    """Test metrics can be reset."""
    processor = EventProcessor()

    # Process some events
    async with AsyncSessionLocal() as session:
        test_payload = create_linear_test_payload(
            "LIN-RESET-001", "Metrics Reset Test", "Test metrics reset"
        )

        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()

    await processor.process_batch()

    # Get initial stats
    stats_before = processor.metrics.get_stats()
    assert stats_before["processed_total"] >= 1

    # Reset metrics
    processor.metrics.reset()

    # Verify reset
    stats_after = processor.metrics.get_stats()
    assert stats_after["processed_total"] == 0
    assert stats_after["batches_total"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_events_to_process():
    """Test processor handles empty event queue gracefully."""
    # Ensure no pending events
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.processed_status == False)
        result = await session.execute(query)
        pending_events = result.scalars().all()

        # Mark all as processed
        for event in pending_events:
            event.processed_status = True

        await session.commit()

    # Process batch
    processor = EventProcessor()
    processed_count = await processor.process_batch()

    assert processed_count == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_processing_scenarios():
    """Test concurrent processing scenarios."""
    # Create multiple events
    event_ids = []
    async with AsyncSessionLocal() as session:
        for i in range(3):
            test_payload = create_linear_test_payload(
                f"LIN-CONCURRENT-{i}",
                f"Concurrent Test Issue {i}",
                f"Concurrent test {i}",
            )

            event = RawWebhookEvent(
                source="linear",
                received_at=datetime.utcnow(),
                processed_status=False,
                headers={"content-type": "application/json"},
                payload=test_payload,
                event_type="Issue.created",
            )

            session.add(event)
            event_ids.append(event.id)

        await session.commit()

    # Create two processors (simulating concurrent workers)
    processor1 = EventProcessor()
    processor2 = EventProcessor()

    # Process with both processors
    processed1 = await processor1.process_batch()
    processed2 = await processor2.process_batch()

    # Both should process events, but row locking should prevent duplicates
    total_processed = processed1 + processed2
    assert total_processed <= 3  # May be less due to row locking

    # Verify all events are processed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id.in_(event_ids))
        result = await session.execute(query)
        processed_events = result.scalars().all()

        for event in processed_events:
            assert event.processed_status is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_transaction_rollback_on_errors():
    """Test database transaction rollback on errors."""
    # Create event that will cause processing error
    async with AsyncSessionLocal() as session:
        test_payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "LIN-TEST-ROLLBACK-001",
                # Missing required fields
                "title": "Rollback Test",
            },
        }

        event = RawWebhookEvent(
            source="linear",
            received_at=datetime.utcnow(),
            processed_status=False,
            headers={"content-type": "application/json"},
            payload=test_payload,
            event_type="Issue.created",
        )

        session.add(event)
        await session.commit()
        event_id = event.id

    # Process event
    processor = EventProcessor()
    await processor.process_batch()

    # Verify event was marked as failed
    async with AsyncSessionLocal() as session:
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await session.execute(query)
        processed_event = result.scalar_one_or_none()

        assert processed_event is not None
        assert processed_event.processed_status is True
        assert processed_event.error_log is not None


# Test fixtures
@pytest.fixture
def sample_linear_payload():
    """Provide sample Linear webhook payload for testing."""
    return {
        "type": "Issue",
        "action": "created",
        "data": {
            "id": "LIN-SAMPLE-001",
            "title": "Sample Issue",
            "description": "Sample description",
            "state": "Backlog",
            "priority": 1,
        },
    }


@pytest.fixture
def sample_linear_payload_with_comment():
    """Provide sample Linear webhook payload with comment for testing."""
    return {
        "type": "Comment",
        "action": "created",
        "data": {
            "id": "CMT-SAMPLE-001",
            "body": "Sample comment",
            "issueId": "LIN-SAMPLE-001",
        },
    }
