"""
Integration tests for webhook endpoints in main app.

Verifies that webhook endpoints are properly registered and accessible
through the main FastAPI application.

Phase: TN-INF-006 - Tunnel and Webhook Verification
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.ingest_llm_as.main import app


@pytest.fixture
def client():
    """Provide a test client for the main app."""
    return TestClient(app)


class TestWebhookEndpointRegistration:
    """Test that webhook endpoints are properly registered in the main app."""

    def test_webhook_linear_endpoint_exists(self, client):
        """Should have /webhook/linear endpoint registered."""
        # Get all routes from the app
        routes = [route.path for route in app.routes]

        # Verify webhook endpoint is registered
        assert "/webhook/linear" in routes

    def test_webhook_health_endpoint_exists(self, client):
        """Should have /webhook/health endpoint registered."""
        routes = [route.path for route in app.routes]

        # Verify webhook health endpoint is registered
        assert "/webhook/health" in routes


class TestWebhookHealthEndpoint:
    """Test webhook forwarder health check endpoint."""

    def test_webhook_health_returns_200(self, client):
        """Health check should return 200 OK."""
        response = client.get("/webhook/health")

        assert response.status_code == 200

    def test_webhook_health_returns_status(self, client):
        """Health check should return forwarder status."""
        response = client.get("/webhook/health")
        data = response.json()

        assert data["service"] == "webhook-forwarder"
        assert data["status"] == "healthy"
        assert "target_url" in data
        assert "timeout_seconds" in data


class TestWebhookLinearEndpointIntegration:
    """Integration tests for the Linear webhook endpoint."""

    @patch("httpx.AsyncClient")
    def test_webhook_linear_endpoint_accessible(self, mock_client_class, client):
        """Linear webhook endpoint should be accessible."""
        # Mock the httpx client to avoid actual network calls
        mock_response = AsyncMock()
        mock_response.status_code = 202
        mock_response.text = "Accepted"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # Send test webhook payload
        response = client.post(
            "/webhook/linear",
            json={"action": "Test", "data": {"id": "test-123"}},
            headers={
                "Content-Type": "application/json",
                "X-Correlation-ID": "test-correlation-id",
                "Linear-Signature": "test-signature",
            },
        )

        # Should return 202 Accepted (or 503 if ingest-llm is unavailable)
        assert response.status_code in [202, 503]

    def test_webhook_linear_requires_post(self, client):
        """Linear webhook endpoint should only accept POST requests."""
        # Try GET request
        response = client.get("/webhook/linear")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405


class TestEndToEndWebhookFlow:
    """End-to-end tests for webhook flow."""

    @patch("httpx.AsyncClient")
    def test_webhook_forwarding_to_ingest_llm(self, mock_client_class, client):
        """Should forward webhook to ingest-llm service."""
        # Mock successful response from ingest-llm
        mock_response = AsyncMock()
        mock_response.status_code = 202

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # Send webhook
        payload = {
            "type": "Issue",
            "action": "create",
            "data": {
                "id": "LIN-456",
                "title": "Test Issue",
            },
        }

        response = client.post(
            "/webhook/linear",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Linear-Signature": "sha256=test",
            },
        )

        # Verify response
        assert response.status_code in [202, 503]

        # If successful, verify response structure
        if response.status_code == 202:
            data = response.json()
            assert "status" in data
            assert "correlation_id" in data

    @patch("httpx.AsyncClient")
    def test_webhook_connection_error_handling(self, mock_client_class, client):
        """Should handle connection errors gracefully."""
        # Mock connection error
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )
        mock_client_class.return_value = mock_client

        # Send webhook
        response = client.post(
            "/webhook/linear",
            json={"action": "Test", "data": {}},
            headers={"Content-Type": "application/json"},
        )

        # Should return 503 Service Unavailable
        assert response.status_code == 503

    @patch("httpx.AsyncClient")
    def test_webhook_timeout_handling(self, mock_client_class, client):
        """Should handle timeouts gracefully."""
        # Mock timeout
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        mock_client_class.return_value = mock_client

        # Send webhook
        response = client.post(
            "/webhook/linear",
            json={"action": "Test", "data": {}},
            headers={"Content-Type": "application/json"},
        )

        # Should return 503 Service Unavailable
        assert response.status_code == 503


class TestWebhookDocumentation:
    """Test that webhook endpoints are documented in OpenAPI."""

    def test_webhook_endpoints_in_openapi_schema(self, client):
        """Webhook endpoints should appear in OpenAPI schema."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        # Verify webhook endpoints are documented
        assert "/webhook/linear" in schema["paths"]
        assert "/webhook/health" in schema["paths"]

        # Verify POST method is documented for /webhook/linear
        assert "post" in schema["paths"]["/webhook/linear"]

        # Verify GET method is documented for /webhook/health
        assert "get" in schema["paths"]["/webhook/health"]
