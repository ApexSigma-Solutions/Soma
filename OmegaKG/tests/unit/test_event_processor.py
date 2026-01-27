"""
Unit Tests for Event Processor (TN-103)

Tests individual components in isolation:
- EventProcessor initialization
- Event routing logic
- Status update methods
- Metrics collection
- Configuration loading
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call
from omega_kg.workers.event_processor import EventProcessor, EventProcessorMetrics
from omega_kg.models.webhook import RawWebhookEvent


@pytest.fixture
def mock_settings():
    with patch("omega_kg.workers.event_processor.settings") as mock:
        mock.webhook_poll_interval = 0.1
        mock.webhook_batch_size = 5
        yield mock


@pytest.mark.asyncio
async def test_process_batch_success_jsonb(mock_settings):
    """Verifies processing with JSONB payload (Dict) and error_log column."""
    # 1. Mock DB
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    # 2. Mock Event (Schema Match) - Fixed: payload should be string/bytes, not dict
    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.id = 123
    mock_event.source = "linear"
    mock_event.payload = '{"type": "Issue", "action": "create"}'  # String format
    mock_event.processed_status = False
    mock_event.error_log = None

    # 3. Query Result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # 4. Patch & Run
    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch(
            "omega_kg.workers.event_processor.get_linear_processor"
        ) as mock_get_lp:
            # Mock Strategy
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(return_value=True)
            mock_get_lp.return_value = mock_lp

            processor = EventProcessor()
            count = await processor.process_batch()

            # 5. Verify
            assert count == 1
            assert mock_event.processed_status is True
            assert mock_event.error_log is None
            mock_lp.process_single_event.assert_called_with(
                {"type": "Issue", "action": "create"}
            )


@pytest.mark.asyncio
async def test_process_batch_failure_logging(mock_settings):
    """Verifies that failures write to error_log."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "unknown"
    mock_event.payload = {"type": "Test"}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        processor = EventProcessor()
        count = await processor.process_batch()

        assert count == 1
        assert mock_event.processed_status is True
        assert mock_event.error_log is not None


@pytest.mark.asyncio
async def test_process_batch_multiple_events(mock_settings):
    """Verifies processing of multiple events in a single batch."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    # Create multiple events
    mock_events = []
    for i in range(3):
        mock_event = MagicMock(spec=RawWebhookEvent)
        mock_event.source = "linear"
        mock_event.payload = f'{{"type": "Issue", "id": {i}}}'
        mock_event.processed_status = False
        mock_event.error_log = None
        mock_events.append(mock_event)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_events
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch(
            "omega_kg.workers.event_processor.get_linear_processor"
        ) as mock_get_lp:
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(return_value=True)
            mock_get_lp.return_value = mock_lp

            processor = EventProcessor()
            count = await processor.process_batch()

            assert count == 3
            assert mock_lp.process_single_event.call_count == 3
            for event in mock_events:
                assert event.processed_status is True


@pytest.mark.asyncio
async def test_process_batch_mixed_success_failure(mock_settings):
    """Verifies batch continues processing after individual failures."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    event1 = MagicMock(spec=RawWebhookEvent)
    event1.source = "linear"
    event1.payload = '{"type": "Issue", "id": 1}'

    event2 = MagicMock(spec=RawWebhookEvent)
    event2.source = "linear"
    event2.payload = '{"type": "Issue", "id": 2}'

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [event1, event2]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch(
            "omega_kg.workers.event_processor.get_linear_processor"
        ) as mock_get_lp:
            mock_lp = MagicMock()
            # First succeeds, second fails
            mock_lp.process_single_event = AsyncMock(
                side_effect=[True, ValueError("Error")]
            )
            mock_get_lp.return_value = mock_lp

            processor = EventProcessor()
            count = await processor.process_batch()

            assert count == 2
            assert event1.processed_status is True
            assert event1.error_log is None
            assert event2.processed_status is True
            assert "Error" in event2.error_log


@pytest.mark.asyncio
async def test_process_batch_empty(mock_settings):
    """Verifies handling of empty batch."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        processor = EventProcessor()
        count = await processor.process_batch()

        assert count == 0


@pytest.mark.asyncio
async def test_process_batch_handler_exception(mock_settings):
    """Verifies exception during handler execution marks event as failed."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "linear"
    mock_event.payload = {"type": "Issue"}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch(
            "omega_kg.workers.event_processor.get_linear_processor"
        ) as mock_get_lp:
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(
                side_effect=ValueError("Test error")
            )
            mock_get_lp.return_value = mock_lp

            processor = EventProcessor()
            count = await processor.process_batch()

            assert count == 1
            assert mock_event.processed_status is True
            assert "Test error" in mock_event.error_log


@pytest.mark.asyncio
async def test_parse_payload_dict():
    """Verifies _parse_payload handles dict correctly."""
    processor = EventProcessor()
    payload = {"type": "Issue", "action": "create"}

    result = processor._parse_payload(payload)
    assert result == {"type": "Issue", "action": "create"}


@pytest.mark.asyncio
async def test_parse_payload_bytes():
    """Verifies _parse_payload handles bytes correctly."""
    processor = EventProcessor()
    payload = b'{"type": "Issue", "action": "create"}'

    result = processor._parse_payload(payload)
    assert result == {"type": "Issue", "action": "create"}


@pytest.mark.asyncio
async def test_parse_payload_string():
    """Verifies _parse_payload handles string correctly."""
    processor = EventProcessor()
    payload = '{"type": "Issue", "action": "create"}'

    result = processor._parse_payload(payload)
    assert result == {"type": "Issue", "action": "create"}


@pytest.mark.asyncio
async def test_parse_payload_invalid_json():
    """Verifies _parse_payload handles invalid JSON gracefully."""
    processor = EventProcessor()
    payload = b"invalid json{"

    result = processor._parse_payload(payload)
    assert result == {}


@pytest.mark.asyncio
async def test_dispatch_unknown_source():
    """Verifies _dispatch handles unknown event sources gracefully."""
    processor = EventProcessor()

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "unknown_platform"

    success, error_msg = await processor._dispatch(mock_event, {"type": "Test"})

    assert success is False
    assert error_msg == "No handler for source 'unknown_platform'"


@pytest.mark.asyncio
async def test_handle_linear_event_success(mock_settings) -> None:
    """Verifies _handle_linear_event processes valid Linear events."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(return_value=True)
        mock_get_lp.return_value = mock_lp

        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue", "action": "create"}

        success, error_msg = await processor._handle_linear_event(mock_event, payload)

        assert success is True, "Should return True on successful processing"
        assert error_msg is None, "Error message should be None on success"
        mock_lp.process_single_event.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_handle_linear_event_failure(mock_settings) -> None:
    """Verifies _handle_linear_event handles processor failures with proper error tracking."""
    # Arrange: Setup mocks with specific exception type
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(
            side_effect=ValueError("Processing error: Invalid payload")
        )
        mock_get_lp.return_value = mock_lp

        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue", "action": "create"}

        # Act: Process the event
        success, error_msg = await processor._handle_linear_event(mock_event, payload)

        # Assert: Verify failure handling
        assert success is False, "Should return False on processing failure"
        assert error_msg is not None, "Error message should be populated"
        assert "Processing error: Invalid payload" in error_msg, (
            "Error message should contain exception details"
        )
        mock_lp.process_single_event.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_handle_linear_event_failure_connection_error(mock_settings) -> None:
    """Verifies _handle_linear_event handles connection errors specifically."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(
            side_effect=ConnectionError("Failed to connect to Linear API")
        )
        mock_get_lp.return_value = mock_lp

        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue"}

        success, error_msg = await processor._handle_linear_event(mock_event, payload)

        assert success is False, "Should return False on connection error"
        assert error_msg is not None, "Error message should be populated"
        assert "Failed to connect to Linear API" in error_msg, (
            "Error message should contain connection details"
        )


@pytest.mark.asyncio
async def test_handle_linear_event_failure_timeout(mock_settings) -> None:
    """Verifies _handle_linear_event handles timeout errors."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(
            side_effect=asyncio.TimeoutError("Request timed out after 30s")
        )
        mock_get_lp.return_value = mock_lp

        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue"}

        success, error_msg = await processor._handle_linear_event(mock_event, payload)

        assert success is False, "Should return False on timeout"
        assert error_msg is not None, "Error message should be populated"
        assert "Request timed out after 30s" in error_msg, (
            "Error message should contain timeout details"
        )


@pytest.mark.asyncio
async def test_handle_linear_event_failure_multiple_errors(mock_settings) -> None:
    """Verifies _handle_linear_event correctly tracks multiple sequential failures."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(
            side_effect=ValueError("Processing error")
        )
        mock_get_lp.return_value = mock_lp

        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue"}

        # Process multiple failing events
        for i in range(3):
            success, error_msg = await processor._handle_linear_event(
                mock_event, payload
            )
            assert success is False, (
                f"Iteration {i}: Should return False on processing failure"
            )
            assert error_msg is not None, (
                f"Iteration {i}: Error message should be populated"
            )


@pytest.mark.asyncio
async def test_handle_linear_event_failure_with_none_payload(mock_settings) -> None:
    """Verifies _handle_linear_event handles None payload gracefully."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(
            side_effect=TypeError("Payload cannot be None")
        )
        mock_get_lp.return_value = mock_lp

        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)

        success, error_msg = await processor._handle_linear_event(mock_event, None)

        assert success is False, "Should return False when payload is None"
        assert error_msg is not None, "Error message should be populated"
        assert "Payload cannot be None" in error_msg, (
            "Error message should contain type error details"
        )


@pytest.mark.asyncio
async def test_mark_complete_updates_event(mock_settings):
    """Verifies _mark_complete updates event correctly."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.processed_status = False
    mock_event.error_log = "previous error"

    processor = EventProcessor()
    processor._mark_complete(mock_session, mock_event)

    assert mock_event.processed_status is True
    assert mock_event.error_log is None


@pytest.mark.asyncio
async def test_mark_failed_truncates_long_errors(mock_settings):
    """Verifies _mark_failed truncates error messages exceeding 1000 chars."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    long_error = "x" * 2000

    processor = EventProcessor()
    processor._mark_failed(mock_session, mock_event, long_error)

    assert mock_event.processed_status is True
    assert len(mock_event.error_log) == 1000


@pytest.mark.asyncio
async def test_start_loop_adaptive_sleep(mock_settings):
    """Verifies start() uses adaptive sleep based on work availability."""
    processor = EventProcessor()

    with patch.object(processor, "process_batch", new_callable=AsyncMock) as mock_batch:
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Define side effect to process events then stop
            async def run_batch():
                # First call: process 5 events
                if mock_batch.call_count == 1:
                    return 5
                # Second call: process 0 events
                elif mock_batch.call_count == 2:
                    return 0
                # Third call: process 0 events and stop
                else:
                    processor.running = False
                    return 0

            mock_batch.side_effect = run_batch

            await processor.start()

            # Verify quick retry after work, longer sleep when idle
            assert mock_sleep.call_count >= 2
            # Check for short sleep (0.1) which happens when events are processed or loop continues
            assert call(0.1) in mock_sleep.call_args_list


@pytest.mark.asyncio
async def test_start_handles_polling_errors(mock_settings):
    """Verifies start() continues after polling errors with backoff."""
    processor = EventProcessor()

    with patch.object(processor, "process_batch", new_callable=AsyncMock) as mock_batch:
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Define side effect to raise error then stop
            async def run_batch_error():
                if mock_batch.call_count == 1:
                    raise Exception("DB error")
                else:
                    processor.running = False
                    return 0

            mock_batch.side_effect = run_batch_error

            await processor.start()

            # Verify backoff sleep after error
            assert call(5.0) in mock_sleep.call_args_list


def test_metrics_initialization():
    """Verifies EventProcessorMetrics initializes correctly."""
    metrics = EventProcessorMetrics()

    assert metrics.processed_count == 0
    assert metrics.error_count == 0
    assert metrics.batch_count == 0
    assert metrics.last_batch_time == 0.0


def test_metrics_record_processed():
    """Verifies metrics record_processed increments correctly."""
    metrics = EventProcessorMetrics()

    metrics.record_processed()
    metrics.record_processed()

    assert metrics.processed_count == 2


def test_metrics_record_error():
    """Verifies metrics record_error increments correctly."""
    metrics = EventProcessorMetrics()

    metrics.record_error()

    assert metrics.error_count == 1


def test_metrics_record_batch():
    """Verifies metrics record_batch updates correctly."""
    metrics = EventProcessorMetrics()

    metrics.record_batch(1.5)

    assert metrics.batch_count == 1
    assert metrics.last_batch_time == 1.5


def test_metrics_get_stats():
    """Verifies get_stats returns correct dictionary."""
    metrics = EventProcessorMetrics()
    metrics.record_processed()
    metrics.record_error()

    stats = metrics.get_stats()

    assert stats["processed_total"] == 1
    assert stats["errors_total"] == 1
    assert "uptime_seconds" in stats


def test_metrics_log_metrics(caplog):
    """Verifies log_metrics outputs correct format."""
    metrics = EventProcessorMetrics()
    metrics.record_processed()
    metrics.record_processed()
    metrics.record_error()

    with caplog.at_level("INFO"):
        metrics.log_metrics()

    assert "processed=2" in caplog.text
    assert "errors=1" in caplog.text


def test_processor_initialization():
    """Verifies EventProcessor initializes with correct handlers."""
    processor = EventProcessor()

    assert processor.running is False
    assert isinstance(processor.metrics, EventProcessorMetrics)
    assert "linear" in processor.handlers


@pytest.mark.asyncio
async def test_stop_sets_running_false():
    """Verifies stop() method sets running flag to False."""
    processor = EventProcessor()
    processor.running = True

    await processor.stop()

    assert processor.running is False


def test_handler_registry_extensibility():
    """Verifies handler registry supports future integrations."""
    processor = EventProcessor()

    # Verify current handler
    assert "linear" in processor.handlers

    # Verify extensibility
    async def mock_handler(event, payload):
        return True

    processor.handlers["github"] = mock_handler
    assert "github" in processor.handlers


@pytest.mark.asyncio
async def test_dispatch_calls_correct_handler(mock_settings):
    """Verifies _dispatch routes to correct handler based on source."""
    mock_handler = AsyncMock(return_value=True)
    processor = EventProcessor()
    processor.handlers["custom"] = mock_handler

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "custom"
    payload = {"type": "CustomEvent"}

    success, error_msg = await processor._dispatch(mock_event, payload)

    assert success is True
    assert error_msg is None
    mock_handler.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_dispatch_handler_exception_handling(mock_settings):
    """Verifies _dispatch handles exceptions from handlers gracefully."""
    mock_handler = AsyncMock(side_effect=RuntimeError("Handler crash"))
    processor = EventProcessor()
    processor.handlers["test"] = mock_handler

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "test"
    payload = {"type": "Test"}

    success, error_msg = await processor._dispatch(mock_event, payload)

    assert success is False
    assert "Handler crash" in error_msg


@pytest.mark.asyncio
async def test_process_batch_query_construction(mock_settings):
    """Verifies process_batch constructs correct database query."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        processor = EventProcessor()
        await processor.process_batch()

        # Verify session was used as context manager
        mock_session.__aenter__.assert_called_once()
        mock_session.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_process_batch_metrics_updated(mock_settings):
    """Verifies process_batch updates metrics correctly."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    events = []
    for i in range(2):
        mock_event = MagicMock(spec=RawWebhookEvent)
        mock_event.source = "linear"
        mock_event.payload = f'{{"id": {i}}}'
        mock_event.processed_status = False
        mock_event.error_log = None
        events.append(mock_event)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = events
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch(
            "omega_kg.workers.event_processor.get_linear_processor"
        ) as mock_get_lp:
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(return_value=True)
            mock_get_lp.return_value = mock_lp

            processor = EventProcessor()
            count = await processor.process_batch()

            assert count == 2
            assert processor.metrics.processed_count == 2


@pytest.mark.asyncio
async def test_parse_payload_nested_json():
    """Verifies _parse_payload handles nested JSON structures."""
    processor = EventProcessor()
    payload = (
        '{"user": {"id": 123, "name": "Test"}, "nested": {"deep": {"value": true}}}'
    )

    result = processor._parse_payload(payload)

    assert result["user"]["id"] == 123
    assert result["nested"]["deep"]["value"] is True


@pytest.mark.asyncio
async def test_parse_payload_empty_string():
    """Verifies _parse_payload handles empty string gracefully."""
    processor = EventProcessor()
    payload = ""

    result = processor._parse_payload(payload)

    assert result == {}


@pytest.mark.asyncio
async def test_parse_payload_empty_bytes():
    """Verifies _parse_payload handles empty bytes gracefully."""
    processor = EventProcessor()
    payload = b""

    result = processor._parse_payload(payload)

    assert result == {}


@pytest.mark.asyncio
async def test_mark_failed_error_truncation_boundary():
    """Verifies _mark_failed correctly truncates at exactly 1000 chars."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    error_message = "x" * 1500

    processor = EventProcessor()
    processor._mark_failed(mock_session, mock_event, error_message)

    assert len(mock_event.error_log) == 1000
    assert mock_event.error_log == "x" * 1000


@pytest.mark.asyncio
async def test_mark_failed_preserves_short_errors():
    """Verifies _mark_failed preserves error messages under 1000 chars."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    short_error = "This is a short error message"

    processor = EventProcessor()
    processor._mark_failed(mock_session, mock_event, short_error)

    assert mock_event.error_log == short_error
    assert len(mock_event.error_log) < 1000


@pytest.mark.asyncio
async def test_handle_linear_event_partial_success():
    """Verifies _handle_linear_event handles partial processor success."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(return_value=False)
        mock_get_lp.return_value = mock_lp

        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue"}

        success, error_msg = await processor._handle_linear_event(mock_event, payload)

        assert success is False


@pytest.mark.asyncio
async def test_process_batch_session_cleanup_on_error(mock_settings):
    """Verifies process_batch cleans up session even on error."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(side_effect=Exception("DB error"))

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        processor = EventProcessor()
        with pytest.raises(Exception):
            await processor.process_batch()

        # Verify session cleanup
        mock_session.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_process_batch_status_transitions(mock_settings):
    """Verifies event status transitions from False to True."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "linear"
    mock_event.payload = '{"type": "Issue"}'
    mock_event.processed_status = False

    assert mock_event.processed_status is False

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch(
            "omega_kg.workers.event_processor.get_linear_processor"
        ) as mock_get_lp:
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(return_value=True)
            mock_get_lp.return_value = mock_lp

            processor = EventProcessor()
            await processor.process_batch()

            assert mock_event.processed_status is True


def test_metrics_error_rate_calculation():
    """Verifies metrics can calculate error rate."""
    metrics = EventProcessorMetrics()
    metrics.record_processed()
    metrics.record_processed()
    metrics.record_error()

    stats = metrics.get_stats()

    assert stats["processed_total"] == 2
    assert stats["errors_total"] == 1
    error_rate = stats["errors_total"] / max(1, stats["processed_total"])
    assert error_rate == 0.5


@pytest.mark.asyncio
async def test_start_loop_respects_running_flag(mock_settings):
    """Verifies start() stops when running flag is set to False."""
    processor = EventProcessor()
    processor.running = True

    with patch.object(processor, "process_batch", new_callable=AsyncMock) as mock_batch:
        # Set running to False on first call completion
        async def stop_on_first_call():
            processor.running = False
            return 0

        mock_batch.side_effect = stop_on_first_call

        await processor.start()

        assert processor.running is False


@pytest.mark.asyncio
async def test_process_batch_handles_payload_parsing_error(mock_settings):
    """Verifies process_batch continues when payload parsing fails."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "linear"
    mock_event.payload = b"corrupted{{{json"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        processor = EventProcessor()
        count = await processor.process_batch()

        assert count == 1
        assert mock_event.processed_status is True
