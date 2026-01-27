"""
Integration tests for Linear Refinery

Tests the complete flow: raw_linear_events → processing → Obsidian markdown
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.domain.linear.processor import (
    process_pending_events,
    process_single_event,
)
from omega_kg.models import RawLinearEvent

# NOTE: Use async_db_session fixture from conftest.py for database tests
# It automatically handles async engine, migrations, and cleanup


@pytest.fixture
def test_vault(tmp_path: Path) -> Path:
    """
    Create temporary test vault directory.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        Path to test vault
    """
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    return vault_path


@pytest.fixture
async def seed_linear_event(async_db_session: AsyncSession):
    """
    Factory fixture to seed RawLinearEvent records.

    Usage:
        await seed_linear_event(
            event_type="Issue",
            action="create",
            body=payload_dict
        )
    """

    async def _seed(
        event_type: str = "Issue",
        action: str = "create",
        body: dict | None = None,
        processed: bool = False,
    ) -> RawLinearEvent:
        """Seed a single event."""
        if body is None:
            # Default payload
            body = {
                "type": "Issue",
                "action": "create",
                "data": {
                    "id": "test-issue-id",
                    "identifier": "APX-123",
                    "title": "Test Issue",
                    "description": "<p>Test description</p>",
                    "priority": 2,
                    "state": {
                        "id": "state-id",
                        "name": "In Progress",
                        "type": "started",
                    },
                    "assignee": {
                        "id": "user-id",
                        "name": "Test User",
                        "email": "test@example.com",
                    },
                    "labels": [{"id": "label-id", "name": "bug"}],
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                },
            }

        event = RawLinearEvent(
            signature="test-signature",
            event_type=event_type,
            action=action,
            headers={"content-type": "application/json"},
            body=body,
            processed=processed,
            received_at=datetime.now(timezone.utc),
        )

        async_db_session.add(event)
        await async_db_session.commit()
        await async_db_session.refresh(event)

        return event

    return _seed


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Async integration tests require transaction isolation; use sync DB fixtures or run tests serially"
)
async def test_process_issue_to_markdown(
    async_db_session: AsyncSession, test_vault: Path, seed_linear_event
):
    """
    Test: Process unprocessed event creates markdown file.

    Given: Unprocessed event in database
    When: process_pending_events is called
    Then: Markdown file created with correct frontmatter and body
    """
    # Seed unprocessed event
    event = await seed_linear_event(processed=False)

    # Process events
    stats = await process_pending_events(async_db_session, test_vault)

    # Assert statistics
    assert stats["processed"] == 1
    assert stats["errors"] == 0
    assert stats["skipped"] == 0

    # Assert file created
    expected_file = test_vault / "Linear" / "[APX-123] Test Issue.md"
    assert expected_file.exists()

    # Assert file content
    content = expected_file.read_text(encoding="utf-8")
    assert "linear_id: test-issue-id" in content
    assert "identifier: APX-123" in content
    assert "status: In Progress" in content
    assert "# Test Issue" in content
    assert "Test description" in content

    # Assert event marked processed
    await async_db_session.refresh(event)
    assert event.processed is True
    assert event.error_log is None


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Async integration tests require transaction isolation; use sync DB fixtures or run tests serially"
)
async def test_duplicate_issue_updates_existing(
    async_db_session: AsyncSession, test_vault: Path, seed_linear_event
):
    """
    Test: Processing same issue identifier updates existing file.

    Given: Existing markdown file for APX-123
    When: New event with updated title is processed
    Then: File is overwritten with new content
    """
    # Seed first event
    await seed_linear_event(processed=False)

    # Process first event
    await process_pending_events(async_db_session, test_vault)

    # Verify initial file
    file_path = test_vault / "Linear" / "[APX-123] Test Issue.md"
    assert file_path.exists()
    # initial_content = file_path.read_text(encoding="utf-8")  # TODO: use for content comparison

    # Seed second event with updated title
    payload = {
        "type": "Issue",
        "action": "update",
        "data": {
            "id": "test-issue-id",
            "identifier": "APX-123",
            "title": "Updated Test Issue",
            "description": "<p>Updated description</p>",
            "priority": 1,
            "state": {"id": "state-id", "name": "Completed", "type": "completed"},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    }
    await seed_linear_event(action="update", body=payload, processed=False)

    # Process second event
    stats = await process_pending_events(async_db_session, test_vault)

    assert stats["processed"] == 1

    # Verify file updated (new filename due to title change)
    new_file_path = test_vault / "Linear" / "[APX-123] Updated Test Issue.md"
    assert new_file_path.exists()

    updated_content = new_file_path.read_text(encoding="utf-8")
    assert "# Updated Test Issue" in updated_content
    assert "status: Completed" in updated_content
    assert "Updated description" in updated_content


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Async integration tests require transaction isolation; use sync DB fixtures or run tests serially"
)
async def test_invalid_event_logs_error(
    async_db_session: AsyncSession, test_vault: Path, seed_linear_event
):
    """
    Test: Invalid payload logs error without failing processing.

    Given: Event with invalid JSON payload
    When: process_pending_events is called
    Then: Error logged to error_log column, processing continues
    """
    # Seed invalid event (missing required fields)
    invalid_payload = {
        "type": "Issue",
        "action": "create",
        "data": {
            # Missing required 'id' and 'identifier'
            "title": "Invalid Issue"
        },
    }
    await seed_linear_event(body=invalid_payload, processed=False)

    # Seed valid event
    await seed_linear_event(processed=False)

    # Process events
    stats = await process_pending_events(async_db_session, test_vault)

    # Assert statistics
    assert stats["processed"] == 1  # Valid event processed
    assert stats["errors"] == 1  # Invalid event logged error
    assert stats["skipped"] == 0

    # Assert valid file created
    expected_file = test_vault / "Linear" / "[APX-123] Test Issue.md"
    assert expected_file.exists()

    # Assert invalid event has error log
    query = select(RawLinearEvent).where(
        RawLinearEvent.body["data"]["title"].astext == "Invalid Issue"
    )
    result = await async_db_session.execute(query)
    invalid_event = result.scalar_one()

    assert invalid_event.processed is False
    assert invalid_event.error_log is not None
    assert "Validation error" in invalid_event.error_log


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Async integration tests require transaction isolation; use sync DB fixtures or run tests serially"
)
async def test_process_single_event_retry(
    async_db_session: AsyncSession, test_vault: Path, seed_linear_event
):
    """
    Test: process_single_event can retry failed events.

    Given: Event with error_log
    When: process_single_event is called with event ID
    Then: Event is reprocessed and marked successful
    """
    # Seed event
    event = await seed_linear_event(processed=False)

    # Manually set error log (simulating previous failure)
    event.error_log = "Previous processing error"
    await async_db_session.commit()

    # Retry processing
    success = await process_single_event(async_db_session, event.id, test_vault)

    assert success is True

    # Assert file created
    expected_file = test_vault / "Linear" / "[APX-123] Test Issue.md"
    assert expected_file.exists()

    # Assert event marked processed with cleared error log
    await async_db_session.refresh(event)
    assert event.processed is True
    assert event.error_log is None


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Async integration tests require transaction isolation; use sync DB fixtures or run tests serially"
)
async def test_skip_events_without_data(
    async_db_session: AsyncSession, test_vault: Path, seed_linear_event
):
    """
    Test: Events without 'data' field are skipped gracefully.

    Given: Event with null data field
    When: process_pending_events is called
    Then: Event is skipped with no error
    """
    # Seed event without data
    payload = {
        "type": "Issue",
        "action": "delete",
        "data": None,  # No data
    }
    await seed_linear_event(body=payload, processed=False)

    # Process events
    stats = await process_pending_events(async_db_session, test_vault)

    # Assert statistics
    assert stats["processed"] == 0
    assert stats["errors"] == 0
    assert stats["skipped"] == 1

    # Assert no files created
    linear_dir = test_vault / "Linear"
    if linear_dir.exists():
        assert len(list(linear_dir.glob("*.md"))) == 0
