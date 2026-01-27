"""
Tests for OmegaClient - HTTP client for OmegaKG Guardian API.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from ingest_llm_as.services.omega_client import OmegaClient


@pytest.fixture
def client():
    """Create client instance for tests."""
    return OmegaClient(
        base_url="http://localhost:8765", api_key="test-api-key", timeout=10
    )


class TestOmegaClient:
    """Test suite for OmegaClient."""

    @pytest.mark.asyncio
    async def test_init_with_default_url(self, client):
        """Test initialization with default URL."""
        assert client.base_url == "http://localhost:8765"
        assert client.api_key == "test-api-key"
        assert client.timeout == 10

    @pytest.mark.asyncio
    async def test_init_with_custom_url(self):
        """Test initialization with custom URL."""
        client = OmegaClient(
            base_url="http://custom.example.com:8765", api_key="custom-key", timeout=20
        )

        assert client.base_url == "http://custom.example.com:8765"
        assert client.api_key == "custom-key"
        assert client.timeout == 20

    @pytest.mark.asyncio
    async def test_commit_data_success(self, client):
        """Test successful commit_data call."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Knowledge committed successfully",
            "storage_results": {
                "graph": {"success": True},
                "vault": {"success": True},
                "vector": {"success": True, "vector_id": "test-vector-123"},
            },
        }

        with patch.object(client._client, "post", return_value=mock_response):
            result = await client.commit_data(
                raw_id="test-conv-001",
                digest={
                    "title": "Test Knowledge",
                    "summary": "Test summary",
                    "entities": [],
                    "concepts": [],
                    "decisions": [],
                    "outcomes": [],
                    "tags": ["test"],
                },
            )

        assert result["success"] is True
        assert result["message"] == "Knowledge committed successfully"
        assert "storage_results" in result
        assert result["storage_results"]["vector"]["vector_id"] == "test-vector-123"

    @pytest.mark.asyncio
    async def test_commit_data_http_error(self, client):
        """Test commit_data with HTTP error."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}

        with patch.object(client._client, "post", return_value=mock_response):
            result = await client.commit_data(
                raw_id="test-conv-002",
                digest={"title": "Error Test", "summary": "Should fail"},
            )

        assert result["success"] is False
        assert result["message"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_commit_data_timeout(self, client):
        """Test commit_data with timeout."""
        with patch.object(
            client._client,
            "post",
            side_effect=httpx.TimeoutException("Request timeout"),
        ):
            result = await client.commit_data(
                raw_id="test-conv-003", digest={"title": "Timeout Test"}
            )

        assert result["success"] is False
        assert result["message"] == "Request timeout after 10s"

    @pytest.mark.asyncio
    async def test_commit_data_network_error(self, client):
        """Test commit_data with network error."""
        with patch.object(
            client._client, "post", side_effect=httpx.NetworkError("Network error")
        ):
            result = await client.commit_data(
                raw_id="test-conv-004", digest={"title": "Network Error Test"}
            )

        assert result["success"] is False
        assert result["message"] == "Network error"

    @pytest.mark.asyncio
    async def test_commit_data_with_metadata(self, client):
        """Test commit_data with metadata."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Knowledge committed successfully",
            "storage_results": {
                "graph": {"success": True},
                "vault": {"success": True},
                "vector": {"success": True, "vector_id": "test-vector-456"},
            },
        }

        with patch.object(client._client, "post", return_value=mock_response):
            result = await client.commit_data(
                raw_id="test-conv-005",
                digest={
                    "title": "Metadata Test",
                    "summary": "Test with metadata",
                    "entities": [],
                    "concepts": [],
                    "decisions": [],
                    "outcomes": [],
                    "tags": [],
                },
                metadata={"platform": "test-platform", "command": "test-cmd"},
            )

        assert result["success"] is True
        assert result["message"] == "Knowledge committed successfully"
        assert result["storage_results"]["vector"]["vector_id"] == "test-vector-456"

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client close method."""
        with patch.object(client._client, "aclose", new_callable=AsyncMock):
            await client.close()
            # Verify close was called
            client._client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager usage."""
        with patch.object(client._client, "aclose", new_callable=AsyncMock):
            async with client as ctx_client:
                # Client should support async context manager
                assert ctx_client is client
            # Verify close was called on exit
            client._client.aclose.assert_called_once()
