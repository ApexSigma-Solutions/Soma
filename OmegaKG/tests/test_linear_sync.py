"""
Unit Tests for LinearSync

Tests LinearSync.update_local_note() method and related functionality.
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest

from omega_kg.linear_sync import (
    LinearSync,
    LinearSyncError,
    LinearAPIError,
    get_linear_sync,
)
from omega_kg.linear_sync import FileNotFoundError as LinearFileNotFoundError


class TestLinearStateMapping:
    """Test Linear state to vault status mapping."""

    def test_map_started_state(self) -> None:
        """Test mapping 'started' state type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            assert (
                sync.map_linear_state_to_vault_status("In Progress", "started")
                == "In Progress"
            )
            assert (
                sync.map_linear_state_to_vault_status("Doing", "started")
                == "In Progress"
            )

    def test_map_completed_state(self) -> None:
        """Test mapping 'completed' state type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            assert sync.map_linear_state_to_vault_status("Done", "completed") == "Done"
            assert (
                sync.map_linear_state_to_vault_status("Complete", "completed") == "Done"
            )

    def test_map_canceled_state(self) -> None:
        """Test mapping 'canceled' state type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            assert (
                sync.map_linear_state_to_vault_status("Canceled", "canceled")
                == "Canceled"
            )
            assert (
                sync.map_linear_state_to_vault_status("Cancelled", "canceled")
                == "Canceled"
            )

    def test_map_backlog_state(self) -> None:
        """Test mapping 'backlog' state type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            assert (
                sync.map_linear_state_to_vault_status("Backlog", "backlog") == "Backlog"
            )
            assert sync.map_linear_state_to_vault_status("Todo", "backlog") == "Backlog"

    def test_map_triage_state(self) -> None:
        """Test mapping 'triage' state type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            assert (
                sync.map_linear_state_to_vault_status("Triage", "triage") == "Backlog"
            )

    def test_map_unknown_state_fallback(self) -> None:
        """Test fallback for unknown state types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            assert (
                sync.map_linear_state_to_vault_status("Unknown", "unknown") == "Backlog"
            )


class TestExtractIssueData:
    """Test issue data extraction from webhook payload."""

    def test_extract_valid_payload(self) -> None:
        """Test extracting data from a valid payload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            payload = {
                "action": "update",
                "type": "Issue",
                "data": {
                    "id": "issue-123",
                    "identifier": "TEST-123",
                    "state": {"name": "Done", "type": "completed"},
                },
            }
            issue_id, state_name, state_type, identifier = sync.extract_issue_data(
                payload
            )
            assert issue_id == "issue-123"
            assert state_name == "Done"
            assert state_type == "completed"
            assert identifier == "TEST-123"

    def test_extract_payload_missing_data(self) -> None:
        """Test error when payload missing 'data' field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            payload = {"action": "update", "type": "Issue"}
            with pytest.raises(KeyError):
                sync.extract_issue_data(payload)

    def test_extract_payload_missing_id(self) -> None:
        """Test error when payload missing 'data.id' field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            payload = {"action": "update", "type": "Issue", "data": {}}
            with pytest.raises(KeyError):
                sync.extract_issue_data(payload)


class TestFindNoteByLinearId:
    """Test finding notes by linear_id."""

    def test_find_existing_note(self) -> None:
        """Test finding a note that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            # Create a test note
            note_content = """---
linear_id: test-issue-456
status: Todo
---
# Test Note
"""
            note_path = vault_path / "Linear" / "TEST-456.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            found = sync.find_note_by_linear_id("test-issue-456")
            assert found == note_path

    def test_find_nonexistent_note(self) -> None:
        """Test finding a note that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            found = sync.find_note_by_linear_id("non-existent-id")
            assert found is None


class TestUpdateLocalNote:
    """Test updating local note with Linear status changes."""

    def test_update_status_success(self) -> None:
        """Test successful status update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            # Create a test note with initial status
            note_content = """---
linear_id: issue-789
status: Todo
identifier: TEST-789
---
# Test Issue
"""
            note_path = vault_path / "Linear" / "TEST-789.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            # Simulate status change in Linear
            payload = {
                "action": "update",
                "type": "Issue",
                "data": {
                    "id": "issue-789",
                    "identifier": "TEST-789",
                    "state": {"name": "Done", "type": "completed"},
                },
            }

            result = sync.update_local_note(payload)
            assert result is True

            # Verify the update
            metadata = sync.vault_utils.read_note_frontmatter(note_path)
            assert metadata.get("status") == "Done"

    def test_update_no_change(self) -> None:
        """Test that no update occurs when status hasn't changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            # Create a test note with same status
            note_content = """---
linear_id: issue-101
status: In Progress
identifier: TEST-101
---
# Test Issue
"""
            note_path = vault_path / "Linear" / "TEST-101.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            # Simulate same status
            payload = {
                "action": "update",
                "type": "Issue",
                "data": {
                    "id": "issue-101",
                    "identifier": "TEST-101",
                    "state": {"name": "In Progress", "type": "started"},
                },
            }

            result = sync.update_local_note(payload)
            assert result is True  # Should succeed, just no change needed

    def test_update_file_not_found(self) -> None:
        """Test error when file not found for linear_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))

            payload = {
                "action": "update",
                "type": "Issue",
                "data": {
                    "id": "non-existent-issue",
                    "identifier": "NON-EXISTENT",
                    "state": {"name": "Done", "type": "completed"},
                },
            }

            with pytest.raises(LinearFileNotFoundError):
                sync.update_local_note(payload)

    def test_update_invalid_payload(self) -> None:
        """Test error when payload is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))

            payload = {"invalid": "payload"}

            with pytest.raises(LinearSyncError):
                sync.update_local_note(payload)

    def test_update_with_fallback_to_identifier(self) -> None:
        """Test fallback to identifier when linear_id search fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            # Create a note with identifier but different linear_id format
            note_content = """---
linear_id: TEST-112
status: Todo
identifier: TEST-112
---
# Test Issue
"""
            note_path = vault_path / "Linear" / "TEST-112.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            payload = {
                "action": "update",
                "type": "Issue",
                "data": {
                    "id": "TEST-112",
                    "identifier": "TEST-112",
                    "state": {"name": "Done", "type": "completed"},
                },
            }

            result = sync.update_local_note(payload)
            assert result is True

            metadata = sync.vault_utils.read_note_frontmatter(note_path)
            assert metadata.get("status") == "Done"


class TestHandleIssueUpdated:
    """Test handle_issue_updated alias method."""

    def test_handle_issue_updated_success(self) -> None:
        """Test successful issue update handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            # Create a test note
            note_content = """---
linear_id: issue-update-test
status: Backlog
identifier: UPDATE-001
---
# Test Issue
"""
            note_path = vault_path / "Linear" / "UPDATE-001.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            payload = {
                "action": "update",
                "type": "Issue",
                "data": {
                    "id": "issue-update-test",
                    "identifier": "UPDATE-001",
                    "state": {"name": "In Progress", "type": "started"},
                },
            }

            result = sync.handle_issue_updated(payload)
            assert result is True

            metadata = sync.vault_utils.read_note_frontmatter(note_path)
            assert metadata.get("status") == "In Progress"


class TestGetLinearSync:
    """Test get_linear_sync convenience function."""

    def test_get_linear_sync(self) -> None:
        """Test getting a LinearSync instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = get_linear_sync(vault_path=Path(tmpdir))
            assert isinstance(sync, LinearSync)


class TestExtractTitleFromContent:
    """Test title extraction from markdown content."""

    def test_extract_title_from_h1(self) -> None:
        """Test extracting title from first H1 heading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            content = "# This is a Test Title\n\nSome content here."
            # pylint: disable=protected-access
            title = sync._extract_title_from_content(content)
            assert title == "This is a Test Title"

    def test_extract_title_no_h1(self) -> None:
        """Test empty string when no H1 present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            content = "Some content without a title."
            # pylint: disable=protected-access
            title = sync._extract_title_from_content(content)
            assert title == ""

    def test_extract_title_with_extra_whitespace(self) -> None:
        """Test title extraction handles whitespace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            content = "#   Title with spaces   \n\nContent"
            # pylint: disable=protected-access
            title = sync._extract_title_from_content(content)
            assert title == "Title with spaces"


class TestMapVaultStatusToLinearState:
    """Test vault status to Linear state mapping."""

    def test_map_backlog_status(self) -> None:
        """Test mapping 'backlog' status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            # pylint: disable=protected-access
            state_id = sync._map_vault_status_to_linear_state("backlog", "team-123")
            assert state_id is None  # Backlog creates without specific state

    def test_map_unknown_status(self) -> None:
        """Test mapping unknown status returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))
            # pylint: disable=protected-access
            state_id = sync._map_vault_status_to_linear_state(
                "unknown_status", "team-123"
            )
            assert state_id is None


class TestCreateFromNote:
    """Test create_from_note outbound sync method."""

    def test_create_from_note_idempotency_skip(self) -> None:
        """Test that existing linear_id causes immediate return (idempotency)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            # Create a note with existing linear_id
            note_content = """---
linear_id: TEST-001
status: Todo
---
# Test Issue

This issue is already synced.
"""
            note_path = vault_path / "Tasks" / "TEST-001.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            # Should return existing ID without calling API
            result = sync.create_from_note(str(note_path))
            assert result == "TEST-001"

    def test_create_from_note_extracts_title_from_frontmatter(self) -> None:
        """Test title extraction prefers frontmatter over H1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            # Create a mock client that doesn't actually call API
            class MockLinearClient:
                # pylint: disable=too-few-public-methods,unused-argument
                async def create_issue(self, **_kwargs: Any) -> dict[str, Any]:
                    return {"id": "new-issue-id", "identifier": "TEST-002"}

            sync.linear_client = MockLinearClient()
            sync.team_id = "team-123"

            note_content = """---
title: Frontmatter Title
status: Todo
---
# H1 Title

Content body here.
"""
            note_path = vault_path / "Tasks" / "TEST-002.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            result = sync.create_from_note(str(note_path))
            assert result == "TEST-002"

            # Verify linear_id was written back
            metadata = sync.vault_utils.read_note_frontmatter(note_path)
            assert metadata.get("linear_id") == "TEST-002"

    def test_create_from_note_extracts_title_from_h1(self) -> None:
        """Test title extraction falls back to H1 when no frontmatter title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            captured_title: list[str] = []

            class MockLinearClient:
                # pylint: disable=too-few-public-methods
                async def create_issue(self, **kwargs: Any) -> dict[str, Any]:
                    captured_title.append(kwargs.get("title", ""))
                    return {"id": "new-issue-id", "identifier": "TEST-003"}

            sync.linear_client = MockLinearClient()
            sync.team_id = "team-123"

            note_content = """---
status: Todo
---
# H1 Title From Content

Content body here.
"""
            note_path = vault_path / "Tasks" / "TEST-003.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            result = sync.create_from_note(str(note_path))
            assert result == "TEST-003"
            assert captured_title[0] == "H1 Title From Content"

    def test_create_from_note_uses_filename_as_fallback(self) -> None:
        """Test filename is used when no title available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            captured_title: list[str] = []

            class MockLinearClient:
                # pylint: disable=too-few-public-methods
                async def create_issue(self, **kwargs: Any) -> dict[str, Any]:
                    captured_title.append(kwargs.get("title", ""))
                    return {"id": "new-issue-id", "identifier": "TEST-004"}

            sync.linear_client = MockLinearClient()
            sync.team_id = "team-123"

            note_content = """---
status: Todo
---
No title here, just content.
"""
            note_path = vault_path / "Tasks" / "my-test-task.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            result = sync.create_from_note(str(note_path))
            assert result == "TEST-004"
            assert captured_title[0] == "my-test-task"  # Filename without extension

    def test_create_from_note_handles_missing_team_id(self) -> None:
        """Test error when LINEAR_TEAM_ID is not configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)
            sync.team_id = None  # No team configured

            note_content = """---
title: Test Issue
---
# Test Issue

Content here.
"""
            note_path = vault_path / "Tasks" / "TEST-005.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            with pytest.raises(LinearSyncError) as exc_info:
                sync.create_from_note(str(note_path))

            assert "LINEAR_TEAM_ID" in str(exc_info.value)

    def test_create_from_note_file_not_found(self) -> None:
        """Test error when note file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            with pytest.raises(LinearSyncError) as exc_info:
                sync.create_from_note(str(vault_path / "nonexistent.md"))

            assert "Failed to read note" in str(exc_info.value)

    def test_create_from_note_preserves_existing_frontmatter(self) -> None:
        """Test that existing frontmatter keys are preserved when writing back linear_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            class MockLinearClient:
                # pylint: disable=too-few-public-methods,unused-argument
                async def create_issue(self, **_kwargs: Any) -> dict[str, Any]:
                    return {"id": "new-issue-id", "identifier": "TEST-006"}

            sync.linear_client = MockLinearClient()
            sync.team_id = "team-123"

            note_content = """---
status: In Progress
priority: high
tags:
  - dev
  - bug
---
# Test Issue

Content body here.
"""
            note_path = vault_path / "Tasks" / "TEST-006.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            sync.create_from_note(str(note_path))

            # Verify all original frontmatter is preserved
            metadata = sync.vault_utils.read_note_frontmatter(note_path)
            assert metadata.get("linear_id") == "TEST-006"
            assert metadata.get("status") == "In Progress"
            assert metadata.get("priority") == "high"
            assert metadata.get("tags") == ["dev", "bug"]

    def test_create_from_note_api_error_handling(self) -> None:
        """Test that API errors are properly caught and wrapped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            sync = LinearSync(vault_path=vault_path)

            class MockLinearClient:
                # pylint: disable=too-few-public-methods,unused-argument
                async def create_issue(self, **_kwargs: Any) -> dict[str, Any]:
                    raise LinearAPIError("API rate limit exceeded")

            sync.linear_client = MockLinearClient()
            sync.team_id = "team-123"

            note_content = """---
title: Test Issue
---
# Test Issue

Content here.
"""
            note_path = vault_path / "Tasks" / "TEST-007.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")

            with pytest.raises(LinearAPIError) as exc_info:
                sync.create_from_note(str(note_path))

            assert "Linear API error" in str(exc_info.value)


class TestLinearSyncExceptions:
    """Test exception handling in LinearSync."""

    def test_file_not_found_returns_none(self) -> None:
        """Test that find_note_by_linear_id returns None when note not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sync = LinearSync(vault_path=Path(tmpdir))

            # Try to find a non-existent note
            found = sync.find_note_by_linear_id("totally-fake-id")
            assert found is None

    def test_linear_api_error_exception(self) -> None:
        """Test LinearAPIError can be raised."""
        with pytest.raises(LinearAPIError):
            raise LinearAPIError("Test API error")
