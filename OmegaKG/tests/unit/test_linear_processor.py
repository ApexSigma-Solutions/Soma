"""
Unit Tests for Linear Processor (TN-103)

Tests LinearProcessor class in isolation:
- LinearProcessor initialization
- process_single_event with various payloads
- TNP file creation
- Embedding generation
- Error handling scenarios
"""

from unittest.mock import patch

import pytest

from omega_kg.domain.linear.processor import LinearProcessor, get_linear_processor


class TestLinearProcessor:
    """Test LinearProcessor class."""

    @pytest.fixture
    def temp_vault_path(self, tmp_path):
        """Create temporary vault path for testing."""
        vault = tmp_path / "test_vault"
        vault.mkdir(parents=True, exist_ok=True)
        return vault

    @pytest.fixture
    def processor(self, temp_vault_path):
        """Create LinearProcessor instance for testing."""
        return LinearProcessor(vault_path=temp_vault_path)

    def test_initialization(self, temp_vault_path):
        """Test LinearProcessor initialization."""
        processor = LinearProcessor(vault_path=temp_vault_path)

        assert processor.vault_path == temp_vault_path
        assert processor.graph_writer is not None
        assert processor.mapper is not None

    @pytest.mark.asyncio
    async def test_process_single_event_success(self, processor, temp_vault_path):
        """Test successful processing of single event."""
        payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "LIN-TEST-001",
                "title": "Test Issue",
                "description": "Test description",
                "state": "Backlog",
                "priority": 1,
            },
        }

        # Mock graph writer and embedding service
        with patch.object(processor.graph_writer, "upsert_issue", return_value=True):
            with patch.object(
                "omega_kg.domain.linear.processor",
                "_generate_embedding",
                return_value=[0.1, 0.2, 0.3],
            ):
                result = await processor.process_single_event(payload)

                assert result is True

                # Verify markdown file was created
                expected_file = temp_vault_path / "01_Active" / "LIN-TEST-001.md"
                assert expected_file.exists()

    @pytest.mark.asyncio
    async def test_process_single_event_no_data(self, processor):
        """Test processing event with no data."""
        payload = {
            "type": "Issue",
            "action": "created",
            "data": None,
        }

        result = await processor.process_single_event(payload)

        # Should return True (skip, not error)
        assert result is True

    @pytest.mark.asyncio
    async def test_process_single_event_validation_error(self, processor):
        """Test processing with invalid payload."""
        payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "LIN-TEST-002",
                # Missing required fields
                "title": "Test Issue 2",
            },
        }

        result = await processor.process_single_event(payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_single_event_graph_error(self, processor):
        """Test handling of graph writer errors."""
        payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "LIN-TEST-003",
                "title": "Test Issue 3",
                "description": "Test description 3",
                "state": "Backlog",
            },
        }

        # Mock graph writer to raise error
        with patch.object(
            processor.graph_writer, "upsert_issue", side_effect=Exception("Graph error")
        ):
            result = await processor.process_single_event(payload)

            # Should return False on graph error
            assert result is False

    @pytest.mark.asyncio
    async def test_process_single_event_embedding_error(self, processor):
        """Test handling of embedding generation errors."""
        payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "LIN-TEST-004",
                "title": "Test Issue 4",
                "description": "Test description 4",
                "state": "Backlog",
            },
        }

        # Mock embedding service to raise error
        with patch.object(
            "omega_kg.domain.linear.processor",
            "_generate_embedding",
            side_effect=Exception("Embedding error"),
        ):
            result = await processor.process_single_event(payload)

            # Should return False on embedding error (non-blocking)
            assert result is False

    @pytest.mark.asyncio
    async def test_create_tnp_if_needed(self, processor, temp_vault_path):
        """Test TNP file creation."""
        payload = {
            "type": "Issue",
            "action": "created",
            "data": {
                "id": "LIN-TEST-TNP-001",
                "title": "TNP Test Issue",
                "description": "Test for TNP creation",
                "state": "Backlog",
            },
        }

        # Mock graph writer
        with patch.object(processor.graph_writer, "upsert_issue", return_value=True):
            # Create template file
            template_path = temp_vault_path / "template_task-note-plan.tnp.md"
            template_path.write_text("# Template", encoding="utf-8")

            result = await processor.process_single_event(payload)

            assert result is True

            # Verify TNP file was created
            tnp_file = temp_vault_path / "01_Active" / "TNP-LIN-TEST-TNP-001.md"
            assert tnp_file.exists()

    def test_close(self, processor):
        """Test close method."""
        # Should not raise any errors
        processor.close()


class TestGetLinearProcessor:
    """Test get_linear_processor singleton function."""

    def test_singleton_returns_same_instance(self):
        """Test that get_linear_processor returns same instance."""
        processor1 = get_linear_processor()
        processor2 = get_linear_processor()

        assert processor1 is processor2

    def test_singleton_initializes_once(self):
        """Test that singleton initializes only once."""
        # Reset singleton
        import omega_kg.domain.linear.processor as processor_module

        processor_module._linear_processor_instance = None

        processor1 = get_linear_processor()
        processor2 = get_linear_processor()

        assert processor1 is processor2
        assert processor1 is not None


class TestLinearProcessorEmbedding:
    """Test embedding generation in LinearProcessor."""

    @pytest.fixture
    def processor(self, temp_vault_path):
        """Create LinearProcessor instance for testing."""
        return LinearProcessor(vault_path=temp_vault_path)

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, processor):
        """Test successful embedding generation."""
        from omega_kg.domain.linear.models import LinearIssue

        issue = LinearIssue(
            id="LIN-TEST-EMB-001",
            title="Test Issue",
            description="Test description",
        )

        # Mock embedding service
        with patch.object(
            "omega_kg.domain.linear.processor",
            "generate_embedding",
            return_value=[0.1, 0.2, 0.3],
        ):
            result = await processor._generate_embedding(issue)

            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_generate_embedding_failure(self, processor):
        """Test embedding generation failure handling."""
        from omega_kg.domain.linear.models import LinearIssue

        issue = LinearIssue(
            id="LIN-TEST-EMB-002",
            title="Test Issue 2",
            description="Test description 2",
        )

        # Mock embedding service to raise error
        with patch.object(
            "omega_kg.domain.linear.processor",
            "generate_embedding",
            side_effect=Exception("Embedding failed"),
        ):
            result = await processor._generate_embedding(issue)

            # Should return None on failure (non-blocking)
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_embedding_payload_construction(self, processor):
        """Test embedding payload construction."""
        from omega_kg.domain.linear.models import LinearIssue

        # Test with title only
        issue_no_desc = LinearIssue(
            id="LIN-TEST-EMB-003",
            title="Title Only",
        )

        with patch.object(
            "omega_kg.domain.linear.processor",
            "generate_embedding",
            return_value=[0.1, 0.2],
        ) as mock_gen:
            await processor._generate_embedding(issue_no_desc)

            # Verify payload was just title
            mock_gen.assert_called_once_with("Title Only")

        # Test with title and description
        issue_with_desc = LinearIssue(
            id="LIN-TEST-EMB-004",
            title="Title With Description",
            description="Test description",
        )

        with patch.object(
            "omega_kg.domain.linear.processor",
            "generate_embedding",
            return_value=[0.3, 0.4],
        ) as mock_gen:
            await processor._generate_embedding(issue_with_desc)

            # Verify payload included both
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args[0][0]
            assert "Title With Description" in call_args
            assert "Test description" in call_args
