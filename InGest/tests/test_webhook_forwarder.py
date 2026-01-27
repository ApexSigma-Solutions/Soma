"""
Unit tests for webhook forwarder shim.

Tests cover request forwarding, error handling, timeout scenarios,
and health check functionality.

Phase: TN-LINEAR-06 - Webhook Ingestion
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import status

from ingest_llm_as.routers.webhook_forwarder import (
    ForwarderSettings,
    forward_linear_webhook,
    forwarder_health,
)


@pytest.fixture
def mock_forwarder_settings():
    """Provide mock forwarder settings for testing."""
    return ForwarderSettings(
        ingest_llm_url="http://test-ingest-llm:8000",
        forwarder_timeout=5,
    )


@pytest.fixture
def sample_webhook_payload():
    """Provide a sample Linear webhook payload."""
    return {
        "action": "IssueCreated",
        "data": {
            "id": "LIN-123",
            "title": "Test Issue",
        },
        "createdAt": "2025-12-29T12:00:00Z",
    }


@pytest.fixture
def sample_correlation_id():
    """Provide a sample correlation ID."""
    return "test-correlation-id-12345"


class TestForwarderSettings:
    """Test forwarder settings initialization."""

    @patch("ingest_llm_as.routers.webhook_forwarder.ForwarderSettings.model_validate")
    def test_default_settings(self, mock_validate):
        """Should use default values when not set."""
        mock_validate.return_value = MagicMock(
            ingest_llm_url="http://ingest-llm:8000",
            forwarder_timeout=5,
        )

        settings = ForwarderSettings()

        assert settings.ingest_llm_url == "http://ingest-llm:8000"
        assert settings.forwarder_timeout == 5

    @patch("ingest_llm_as.routers.webhook_forwarder.ForwarderSettings.model_validate")
    def test_custom_settings_from_env(self, mock_validate):
        """Should load custom settings from environment."""
        mock_validate.return_value = MagicMock(
            ingest_llm_url="http://custom-ingest:9000",
            forwarder_timeout=10,
        )

        with patch.dict(
            "os.environ",
            {
                "FORWARDER_INGEST_LLM_URL": "http://custom-ingest:9000",
                "FORWARDER_FORWARDER_TIMEOUT": "10",
            },
            clear=True,
        ):
            settings = ForwarderSettings()

        assert settings.ingest_llm_url == "http://custom-ingest:9000"
        assert settings.forwarder_timeout == 10


class TestForwardLinearWebhookSuccess:
    """Test successful webhook forwarding."""

    @pytest.mark.asyncio
    async def test_forward_webhook_success(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
        sample_correlation_id,
    ):
        """Successfully forwarding webhook should return 202."""
        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = status.HTTP_202_ACCEPTED
        mock_response.text = "Webhook processed"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await forward_linear_webhook(
                request=MagicMock(
                    body=AsyncMock(return_value=sample_webhook_payload.encode()),
                    headers={
                        "Content-Type": "application/json",
                        "X-Correlation-ID": sample_correlation_id,
                        "Linear-Signature": "test-signature",
                    },
                )
            )

        # Verify response
        assert result["status"] == "forwarded"
        assert result["correlation_id"] == sample_correlation_id
        assert "message" in result


class TestForwardLinearWebhookTimeout:
    """Test timeout scenarios."""

    @pytest.mark.asyncio
    async def test_forward_webhook_timeout(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
        sample_correlation_id,
    ):
        """Timeout should return 503 Service Unavailable."""
        # Mock httpx client to raise timeout
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await forward_linear_webhook(
                    request=MagicMock(
                        body=AsyncMock(return_value=sample_webhook_payload.encode()),
                        headers={
                            "Content-Type": "application/json",
                            "X-Correlation-ID": sample_correlation_id,
                            "Linear-Signature": "test-signature",
                        },
                    )
                )

        # Verify exception is HTTP 503
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "timeout" in exc_info.value.detail.lower()


class TestForwardLinearWebhookConnectionError:
    """Test connection error scenarios."""

    @pytest.mark.asyncio
    async def test_forward_webhook_connection_error(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
        sample_correlation_id,
    ):
        """Connection error should return 503 Service Unavailable."""
        # Mock httpx client to raise connection error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await forward_linear_webhook(
                    request=MagicMock(
                        body=AsyncMock(return_value=sample_webhook_payload.encode()),
                        headers={
                            "Content-Type": "application/json",
                            "X-Correlation-ID": sample_correlation_id,
                            "Linear-Signature": "test-signature",
                        },
                    )
                )

        # Verify exception is HTTP 503
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "unavailable" in exc_info.value.detail.lower()


class TestForwardLinearWebhookHTTPError:
    """Test HTTP error scenarios."""

    @pytest.mark.asyncio
    async def test_forward_webhook_http_error(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
        sample_correlation_id,
    ):
        """HTTP error should return 503 Service Unavailable."""
        # Mock httpx client to raise HTTP status error
        mock_response = AsyncMock()
        mock_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_response.text = "Internal server error"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await forward_linear_webhook(
                    request=MagicMock(
                        body=AsyncMock(return_value=sample_webhook_payload.encode()),
                        headers={
                            "Content-Type": "application/json",
                            "X-Correlation-ID": sample_correlation_id,
                            "Linear-Signature": "test-signature",
                        },
                    )
                )

        # Verify exception is HTTP 503
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "error" in exc_info.value.detail.lower()


class TestForwardLinearWebhookUnexpectedError:
    """Test unexpected error scenarios."""

    @pytest.mark.asyncio
    async def test_forward_webhook_unexpected_error(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
        sample_correlation_id,
    ):
        """Unexpected errors should return 500 Internal Server Error."""
        # Mock httpx client to raise unexpected error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await forward_linear_webhook(
                    request=MagicMock(
                        body=AsyncMock(return_value=sample_webhook_payload.encode()),
                        headers={
                            "Content-Type": "application/json",
                            "X-Correlation-ID": sample_correlation_id,
                            "Linear-Signature": "test-signature",
                        },
                    )
                )

        # Verify exception is HTTP 500
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "unexpected" in exc_info.value.detail.lower()


class TestForwardLinearWebhookUnexpectedStatus:
    """Test unexpected status code scenarios."""

    @pytest.mark.asyncio
    async def test_forward_webhook_unexpected_status(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
        sample_correlation_id,
    ):
        """Unexpected status codes should be forwarded as-is."""
        # Mock httpx client to return unexpected status
        mock_response = AsyncMock()
        mock_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_response.text = "Server error"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await forward_linear_webhook(
                request=MagicMock(
                    body=AsyncMock(return_value=sample_webhook_payload.encode()),
                    headers={
                        "Content-Type": "application/json",
                        "X-Correlation-ID": sample_correlation_id,
                        "Linear-Signature": "test-signature",
                    },
                )
            )

        # Verify exception is raised with unexpected status
        assert "500" in result["message"]


class TestForwardLinearWebhookHeaders:
    """Test header forwarding."""

    @pytest.mark.asyncio
    async def test_forward_webhook_preserves_headers(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
        sample_correlation_id,
    ):
        """Should preserve important headers when forwarding."""
        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = status.HTTP_202_ACCEPTED

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        captured_post_call = None

        def capture_post_call(*args, **kwargs):
            nonlocal captured_post_call
            captured_post_call = kwargs

        mock_client.__aenter__.return_value.post.side_effect = capture_post_call

        with patch("httpx.AsyncClient", return_value=mock_client):
            await forward_linear_webhook(
                request=MagicMock(
                    body=AsyncMock(return_value=sample_webhook_payload.encode()),
                    headers={
                        "Content-Type": "application/json",
                        "X-Correlation-ID": sample_correlation_id,
                        "Linear-Signature": "test-signature",
                    },
                )
            )

        # Verify headers were forwarded
        assert captured_post_call is not None
        assert "headers" in captured_post_call
        assert captured_post_call["headers"]["Content-Type"] == "application/json"
        assert (
            captured_post_call["headers"]["X-Correlation-ID"] == sample_correlation_id
        )
        assert captured_post_call["headers"]["Linear-Signature"] == "test-signature"


class TestForwarderHealth:
    """Test forwarder health check endpoint."""

    @pytest.mark.asyncio
    async def test_forwarder_health(self, mock_forwarder_settings):
        """Health check should return forwarder status."""
        result = await forwarder_health()

        assert result["service"] == "webhook-forwarder"
        assert result["status"] == "healthy"
        assert result["target_url"] == mock_forwarder_settings.ingest_llm_url
        assert result["timeout_seconds"] == mock_forwarder_settings.forwarder_timeout


class TestForwarderEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_forward_webhook_empty_payload(
        self,
        mock_forwarder_settings,
        sample_correlation_id,
    ):
        """Empty payload should be forwarded correctly."""
        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = status.HTTP_202_ACCEPTED

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await forward_linear_webhook(
                request=MagicMock(
                    body=AsyncMock(return_value=b""),
                    headers={
                        "Content-Type": "application/json",
                        "X-Correlation-ID": sample_correlation_id,
                        "Linear-Signature": "test-signature",
                    },
                )
            )

        # Verify response
        assert result["status"] == "forwarded"

    @pytest.mark.asyncio
    async def test_forward_webhook_large_payload(
        self,
        mock_forwarder_settings,
        sample_correlation_id,
    ):
        """Large payloads should be forwarded correctly."""
        # Create a large payload
        large_payload = {"data": "x" * 10000}

        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = status.HTTP_202_ACCEPTED

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await forward_linear_webhook(
                request=MagicMock(
                    body=AsyncMock(return_value=large_payload.encode()),
                    headers={
                        "Content-Type": "application/json",
                        "X-Correlation-ID": sample_correlation_id,
                        "Linear-Signature": "test-signature",
                    },
                )
            )

        # Verify response
        assert result["status"] == "forwarded"

    @pytest.mark.asyncio
    async def test_forward_webhook_missing_correlation_id(
        self,
        mock_forwarder_settings,
        sample_webhook_payload,
    ):
        """Missing correlation ID should use default value."""
        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = status.HTTP_202_ACCEPTED

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await forward_linear_webhook(
                request=MagicMock(
                    body=AsyncMock(return_value=sample_webhook_payload.encode()),
                    headers={
                        "Content-Type": "application/json",
                        "Linear-Signature": "test-signature",
                    },
                )
            )

        # Verify default correlation ID is used
        assert result["correlation_id"] == "unknown"
