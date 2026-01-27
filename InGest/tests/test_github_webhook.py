"""
Integration tests for GitHub webhook endpoint in InGest-LLM.
"""

import hashlib
import hmac
import json
import os
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from ingest_llm_as.main import app

# Sample payload for testing
GITHUB_PAYLOAD = {
    "action": "closed",
    "pull_request": {
        "url": "https://api.github.com/repos/octocat/Hello-World/pulls/1347",
        "id": 1,
        "title": "Amazing new feature",
        "user": {
            "login": "octocat",
        },
        "body": "Please pull these awesome changes in!",
        "merged": True,
    },
    "repository": {
        "full_name": "octocat/Hello-World",
    },
}


class TestGitHubWebhookIntegration:
    """Integration tests for GitHub webhook endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def _create_signature(self, payload: dict, secret: str) -> str:
        """Create valid GitHub webhook signature."""
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @patch.dict(
        os.environ,
        {
            "GITHUB_WEBHOOK_SECRET": "test-secret",
            "POSTGRES_DSN": "postgresql://user:pass@localhost:5432/db",
        },
    )
    def test_webhook_valid_signature(self, client):
        """Test webhook accepts request with valid signature."""
        payload = GITHUB_PAYLOAD
        signature = self._create_signature(payload, "test-secret")

        # Mock the saga and circuit breaker to avoid side effects
        with (
            patch(
                "ingest_llm_as.routers.webhook.saga.begin_transaction",
                new_callable=AsyncMock,
            ) as mock_begin,
            patch(
                "ingest_llm_as.routers.webhook.saga.commit_transaction",
                new_callable=AsyncMock,
            ) as mock_commit,
            patch(
                "ingest_llm_as.routers.webhook._process_github_webhook_payload",
                new_callable=AsyncMock,
            ) as mock_process,
        ):
            response = client.post(
                "/api/v1/webhook/github",
                json=payload,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Delivery": "test-id",
                },
            )

            assert response.status_code == 202
            assert response.json()["status"] == "accepted"

            mock_begin.assert_called_once()
            mock_process.assert_called_once()
            mock_commit.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": "test-secret"})
    def test_webhook_invalid_signature(self, client):
        """Test webhook rejects request with invalid signature."""
        payload = GITHUB_PAYLOAD
        # Create signature with wrong secret
        signature = self._create_signature(payload, "wrong-secret")

        response = client.post(
            "/api/v1/webhook/github",
            json=payload,
            headers={"X-Hub-Signature-256": signature},
        )

        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]["message"]

    @patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": "test-secret"})
    def test_webhook_missing_signature(self, client):
        """Test webhook rejects request without signature."""
        response = client.post(
            "/api/v1/webhook/github",
            json=GITHUB_PAYLOAD,
        )

        # In the implementation, verify_signature returns False if signature is missing or None
        # And if verify_signature returns False, it raises 401
        assert response.status_code == 401

    @patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": "test-secret"})
    def test_webhook_circuit_breaker_open(self, client):
        """Test webhook rejects request when circuit breaker is open."""

        # We need to target the specific instance in the router module
        with patch(
            "ingest_llm_as.routers.webhook.github_circuit_breaker.is_closed",
            return_value=False,
        ):
            response = client.post(
                "/api/v1/webhook/github",
                json=GITHUB_PAYLOAD,
                headers={"X-Hub-Signature-256": "any-sig"},
            )

            assert response.status_code == 503
            assert "Circuit breaker is open" in response.json()["detail"]["message"]

    @patch.dict(
        os.environ,
        {
            "GITHUB_WEBHOOK_SECRET": "test-secret",
            "POSTGRES_DSN": "postgresql://user:pass@localhost:5432/db",
        },
    )
    def test_webhook_processing_failure_dlq(self, client):
        """Test that processing failures are written to DLQ."""
        payload = GITHUB_PAYLOAD
        signature = self._create_signature(payload, "test-secret")

        # Mock processing to fail
        with (
            patch(
                "ingest_llm_as.routers.webhook.saga.begin_transaction",
                new_callable=AsyncMock,
            ),
            patch(
                "ingest_llm_as.routers.webhook._process_github_webhook_payload",
                side_effect=Exception("Processing failed"),
            ) as mock_process,
            patch(
                "ingest_llm_as.routers.webhook.write_to_dlq", new_callable=AsyncMock
            ) as mock_dlq,
            patch(
                "ingest_llm_as.routers.webhook.record_dlq_message"
            ) as mock_record_dlq,
            patch(
                "ingest_llm_as.routers.webhook.record_webhook_request"
            ) as mock_record_request,
        ):
            mock_dlq.return_value = "dlq-entry-id"

            response = client.post(
                "/api/v1/webhook/github",
                json=payload,
                headers={"X-Hub-Signature-256": signature},
            )

            assert response.status_code == 500
            assert "Failed to process webhook" in response.json()["detail"]["message"]

            mock_process.assert_called_once()
            mock_dlq.assert_called_once()
            mock_record_dlq.assert_called_once()
            mock_record_request.assert_called_once()
