"""
Unit tests for GitHub event processor.

Tests the core business logic of parsing "Fixes [TEAM-ID]" patterns
and updating Linear issues.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from omega_kg.domain.github.processor import (
    GitHubProcessor,
    ISSUE_REFERENCE_PATTERN,
)
from omega_kg.domain.github.models import ParsedIssueReference
from omega_kg.github_client import GitHubClient


class TestIssueReferencePattern:
    """Test the regex pattern for parsing issue references."""

    def test_fixes_pattern(self):
        """Test parsing of 'Fixes [TEAM-ID]' pattern."""
        message = "Fixes [PROJ-123] - Add authentication fix"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == ["PROJ-123"]

    def test_closes_pattern(self):
        """Test parsing of 'Closes [TEAM-ID]' pattern."""
        message = "Closes [LIN-456] - Resolve API issue"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == ["LIN-456"]

    def test_resolves_pattern(self):
        """Test parsing of 'Resolves [TEAM-ID]' pattern."""
        message = "Resolves [TEAM-789] - Update documentation"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == ["TEAM-789"]

    def test_multiple_references(self):
        """Test parsing multiple issue references in one message."""
        message = "Fixes [PROJ-123]\nCloses [LIN-456]"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == ["PROJ-123", "LIN-456"]

    def test_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        message = "FIXES [PROJ-123] - Authentication fix"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == ["PROJ-123"]

        message = "closes [LIN-456]"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == ["LIN-456"]

    def test_complex_commit_message(self):
        """Test parsing in a realistic commit message."""
        message = """
        Implement user authentication

        - Add JWT token validation
        - Add management
        - session Fixes [PROJ-123] - Security vulnerability
        - Closes [LIN-456] - User login issue
        """
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert "PROJ-123" in matches
        assert "LIN-456" in matches
        assert len(matches) == 2

    def test_no_references(self):
        """Test commit message without issue references."""
        message = "Update README with new instructions"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == []

    def test_wrong_format(self):
        """Test that incorrectly formatted references are not matched."""
        message = "Fixes PROJ-123 without brackets"
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == []

        message = "Fixes [PROJ-123"  # Missing closing bracket
        matches = ISSUE_REFERENCE_PATTERN.findall(message)
        assert matches == []


class TestGitHubProcessor:
    """Test the GitHubProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create a GitHubProcessor instance with mocked clients."""
        with patch("omega_kg.domain.github.processor.GitHubClient"):
            with patch("omega_kg.domain.github.processor.LinearClient"):
                processor = GitHubProcessor()
                processor.github_client = Mock(spec=GitHubClient)
                processor.linear_client = Mock()
                return processor

    @pytest.mark.asyncio
    async def test_process_single_event_non_merge(self):
        """Test processing a non-merge event (should be ignored)."""
        with patch("omega_kg.domain.github.processor.GitHubClient"):
            with patch("omega_kg.domain.github.processor.LinearClient"):
                processor = GitHubProcessor()

        payload = {
            "action": "opened",
            "pull_request": {"merged": False},
            "repository": {"full_name": "user/repo"},
        }

        result = await processor.process_single_event(payload)
        assert result is True  # Should succeed but do nothing

    @pytest.mark.asyncio
    async def test_process_single_event_merge(self):
        """Test processing a merge event."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)
        processor.github_client.get_pull_request_commits = AsyncMock(return_value=[])
        processor.linear_client = Mock()

        payload = {
            "action": "closed",
            "pull_request": {"merged": True, "number": 42},
            "repository": {
                "name": "repo",
                "full_name": "user/repo",
                "owner": {"login": "user"},
            },
        }

        result = await processor.process_single_event(payload)
        assert result is True

    @pytest.mark.asyncio
    async def test_extract_issue_references(self):
        """Test extraction of issue references from commits."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)

        # Mock GitHub API response with commits
        commits = [
            {
                "sha": "abc123def456",
                "commit": {"message": "Fixes [PROJ-123] - Add auth fix"},
            },
            {
                "sha": "789ghi012jkl",
                "commit": {"message": "Closes [LIN-456] - Update API"},
            },
        ]
        processor.github_client.get_pull_request_commits = AsyncMock(
            return_value=commits
        )

        refs = await processor._extract_issue_references("user", "repo", 42)

        assert len(refs) == 2
        assert refs[0].identifier == "PROJ-123"
        assert refs[0].pattern == "fixes"
        assert refs[0].commit_sha == "abc123de"
        assert refs[1].identifier == "LIN-456"
        assert refs[1].pattern == "closes"
        assert refs[1].commit_sha == "789ghi01"

    @pytest.mark.asyncio
    async def test_extract_issue_references_no_matches(self):
        """Test extraction when no issue references are found."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)

        # Mock GitHub API response with commits but no issue references
        commits = [
            {
                "sha": "abc123",
                "commit": {"message": "Update README with new instructions"},
            }
        ]
        processor.github_client.get_pull_request_commits = AsyncMock(
            return_value=commits
        )

        refs = await processor._extract_issue_references("user", "repo", 42)

        assert len(refs) == 0

    @pytest.mark.asyncio
    async def test_update_linear_issue_success(self):
        """Test successful Linear issue update."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)
        processor.linear_client = Mock()

        # Mock Linear issue response
        processor.linear_client.get_issue = AsyncMock(
            return_value={
                "id": "issue-123",
                "state": {"id": "state-456"},
            }
        )
        processor.linear_client.update_issue = AsyncMock()

        with patch("omega_kg.settings.settings") as mock_settings:
            mock_settings.linear_done_state_id = "done-state-789"

            result = await processor._update_linear_issue("PROJ-123")

        assert result is True
        processor.linear_client.get_issue.assert_called_once_with("PROJ-123")
        processor.linear_client.update_issue.assert_called_once_with(
            issue_id="issue-123", updates={"stateId": "done-state-789"}
        )

    @pytest.mark.asyncio
    async def test_update_linear_issue_not_found(self):
        """Test update when Linear issue doesn't exist."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)
        processor.linear_client = Mock()

        processor.linear_client.get_issue = AsyncMock(return_value=None)

        result = await processor._update_linear_issue("NONEXISTENT-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_update_linear_issue_already_done(self):
        """Test update when issue is already in done state."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)
        processor.linear_client = Mock()

        processor.linear_client.get_issue = AsyncMock(
            return_value={
                "id": "issue-123",
                "state": {"id": "done-state-789"},  # Already done
            }
        )

        with patch("omega_kg.settings.settings") as mock_settings:
            mock_settings.linear_done_state_id = "done-state-789"

            result = await processor._update_linear_issue("PROJ-123")

        assert result is True
        # Should not call update_issue if already done
        processor.linear_client.update_issue.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_linear_issue_no_state_id(self):
        """Test update when LINEAR_DONE_STATE_ID is not configured."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)
        processor.linear_client = Mock()

        with patch("omega_kg.settings.settings") as mock_settings:
            mock_settings.linear_done_state_id = None

            result = await processor._update_linear_issue("PROJ-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_pr_merged_with_references(self):
        """Test PR merge handling with issue references."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)
        processor.linear_client = Mock()

        processor.github_client.get_pull_request_commits = AsyncMock(
            return_value=[
                {
                    "sha": "abc123",
                    "commit": {"message": "Fixes [PROJ-123] - Auth fix"},
                }
            ]
        )
        processor.linear_client.get_issue = AsyncMock(
            return_value={"id": "issue-123", "state": {"id": "state-456"}}
        )
        processor.linear_client.update_issue = AsyncMock()

        payload = {
            "action": "closed",
            "pull_request": {"merged": True, "number": 42},
            "repository": {
                "name": "repo",
                "full_name": "user/repo",
                "owner": {"login": "user"},
            },
        }

        with patch("omega_kg.settings.settings") as mock_settings:
            mock_settings.linear_done_state_id = "done-state-789"

            result = await processor._handle_pr_merged(payload)

        assert result is True
        processor.linear_client.update_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_pr_merged_no_references(self):
        """Test PR merge handling without issue references."""
        processor = GitHubProcessor()
        processor.github_client = Mock(spec=GitHubClient)
        processor.linear_client = Mock()

        # No issue references in commits
        processor.github_client.get_pull_request_commits = AsyncMock(
            return_value=[
                {
                    "sha": "abc123",
                    "commit": {"message": "Update README"},
                }
            ]
        )

        payload = {
            "action": "closed",
            "pull_request": {"merged": True, "number": 42},
            "repository": {
                "name": "repo",
                "full_name": "user/repo",
                "owner": {"login": "user"},
            },
        }

        result = await processor._handle_pr_merged(payload)

        assert result is True
        # Should not update any Linear issues
        processor.linear_client.update_issue.assert_not_called()


class TestParsedIssueReference:
    """Test the ParsedIssueReference model."""

    def test_create_reference(self):
        """Test creating a ParsedIssueReference."""
        ref = ParsedIssueReference(
            identifier="PROJ-123",
            pattern="fixes",
            commit_sha="abc123",
        )

        assert ref.identifier == "PROJ-123"
        assert ref.pattern == "fixes"
        assert ref.commit_sha == "abc123"

    def test_reference_without_commit(self):
        """Test creating a reference without commit SHA."""
        ref = ParsedIssueReference(identifier="PROJ-123", pattern="closes")

        assert ref.identifier == "PROJ-123"
        assert ref.pattern == "closes"
        assert ref.commit_sha is None
