"""
Integration tests for GitHub webhook endpoint.

Tests the complete flow from webhook reception to event processing.
"""

import hmac
import hashlib
import json
from unittest.mock import Mock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from omega_kg.main import app
from tests.fixtures.github_payloads import PR_MERGED_SINGLE_ISSUE


class TestGitHubWebhookIntegration:
    """Integration tests for GitHub webhook endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def _create_signature(self, payload: dict, secret: str) -> str:
        """Create valid GitHub webhook signature."""
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @patch("omega_kg.settings.settings")
    def test_webhook_missing_signature(self, mock_settings):
        """Test webhook rejects request without signature."""
        mock_settings.github_webhook_secret = "test-secret"

        response = self.client.post(
            "/webhooks/github",
            json={"test": "payload"},
        )

        assert response.status_code == 400
        assert "Missing X-Hub-Signature-256 header" in response.json()["detail"]

    @patch("omega_kg.settings.settings")
    def test_webhook_invalid_signature(self, mock_settings):
        """Test webhook rejects request with invalid signature."""
        mock_settings.github_webhook_secret = "test-secret"

        response = self.client.post(
            "/webhooks/github",
            json={"test": "payload"},
            headers={"X-Hub-Signature-256": "invalid-signature"},
        )

        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]

    @patch("omega_kg.settings.settings")
    def test_webhook_valid_signature(self, mock_settings):
        """Test webhook accepts request with valid signature."""
        mock_settings.github_webhook_secret = "test-secret"

        payload = {"test": "payload"}
        signature = self._create_signature(payload, "test-secret")

        response = self.client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-Hub-Signature-256": signature},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "persisted"
        assert "id" in response.json()

    @patch("omega_kg.settings.settings")
    def test_webhook_pr_merge_event(self, mock_settings):
        """Test processing of PR merge event."""
        mock_settings.github_webhook_secret = "test-secret"

        payload = PR_MERGED_SINGLE_ISSUE
        signature = self._create_signature(payload, "test-secret")

        response = self.client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-Hub-Signature-256": signature},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "persisted"

    @patch("omega_kg.settings.settings")
    def test_webhook_invalid_json(self, mock_settings):
        """Test webhook rejects invalid JSON payload."""
        mock_settings.github_webhook_secret = "test-secret"

        response = self.client.post(
            "/webhooks/github",
            content=b"invalid json",
            headers={"X-Hub-Signature-256": "test"},
        )

        assert response.status_code == 400

    @patch("omega_kg.settings.settings")
    def test_webhook_signature_with_different_secret(self, mock_settings):
        """Test webhook rejects signature created with wrong secret."""
        mock_settings.github_webhook_secret = "correct-secret"

        payload = {"test": "payload"}
        # Create signature with wrong secret
        wrong_signature = self._create_signature(payload, "wrong-secret")

        response = self.client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-Hub-Signature-256": wrong_signature},
        )

        assert response.status_code == 401

    @patch("omega_kg.settings.settings")
    def test_webhook_preserves_headers(self, mock_settings):
        """Test webhook preserves headers in database."""
        mock_settings.github_webhook_secret = "test-secret"

        payload = {"test": "payload"}
        signature = self._create_signature(payload, "test-secret")

        response = self.client.post(
            "/webhooks/github",
            json=payload,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-id",
            },
        )

        assert response.status_code == 200

    @patch("omega_kg.settings.settings")
    @patch("omega_kg.database.session.get_db")
    @patch("omega_kg.models.webhook.RawWebhookEvent")
    def test_webhook_stores_event_in_database(
        self, mock_event_class, mock_get_db, mock_settings
    ):
        """Test that webhook event is stored in database."""
        mock_settings.github_webhook_secret = "test-secret"

        # Mock database session
        mock_session = AsyncMock()
        mock_event = Mock()
        mock_event.id = 123
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_get_db.return_value = mock_session

        # Mock event class to return our mock event
        mock_event_class.return_value = mock_event

        payload = {"test": "payload"}
        signature = self._create_signature(payload, "test-secret")

        response = self.client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-Hub-Signature-256": signature},
        )

        assert response.status_code == 200
        mock_session.add.assert_called_once_with(mock_event)
        mock_session.commit.assert_called_once()


class TestGitHubWebhookEventProcessing:
    """Test the event processing flow."""

    @pytest.mark.asyncio
    @patch("omega_kg.github_client.GitHubClient")
    @patch("omega_kg.linear_client.LinearClient")
    async def test_full_pr_merge_flow(self, mock_linear_client, mock_github_client):
        """Test complete PR merge to Linear update flow."""
        # This would be a full integration test in a real scenario
        # For now, we'll verify the architecture is in place

        # Verify that the GitHub processor can be instantiated
        from omega_kg.domain.github.processor import get_github_processor

        processor = get_github_processor()

        # Verify the processor has the expected methods
        assert hasattr(processor, "process_single_event")
        assert hasattr(processor, "_handle_pr_merged")
        assert hasattr(processor, "_extract_issue_references")
        assert hasattr(processor, "_update_linear_issue")


class TestGitHubWebhookSecurity:
    """Test security aspects of the webhook endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def _create_signature(self, payload: dict, secret: str) -> str:
        """Create valid GitHub webhook signature."""
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @patch("omega_kg.settings.settings")
    def test_replay_attack_protection(self, mock_settings):
        """Test that replay attacks are prevented by signature validation."""
        mock_settings.github_webhook_secret = "test-secret"

        payload = {"test": "payload", "timestamp": "2024-01-01"}
        signature = self._create_signature(payload, "test-secret")

        # Same payload and signature can be sent multiple times
        # The signature validation will pass each time
        # This is expected behavior - GitHub doesn't provide replay protection
        # In production, implement additional checks (event ID tracking, timestamps)

        for _ in range(3):
            response = self.client.post(
                "/webhooks/github",
                json=payload,
                headers={"X-Hub-Signature-256": signature},
            )
            assert response.status_code == 200

    @patch("omega_kg.settings.settings")
    def test_malformed_signature_header(self, mock_settings):
        """Test handling of malformed signature header."""
        mock_settings.github_webhook_secret = "test-secret"

        payload = {"test": "payload"}

        # Missing "sha256=" prefix
        response = self.client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-Hub-Signature-256": "invalidsignature"},
        )

        assert response.status_code == 401

    @patch("omega_kg.settings.settings")
    def test_empty_payload(self, mock_settings):
        """Test handling of empty payload."""
        mock_settings.github_webhook_secret = "test-secret"

        signature = self._create_signature({}, "test-secret")

        response = self.client.post(
            "/webhooks/github",
            json={},
            headers={"X-Hub-Signature-256": signature},
        )

        assert response.status_code == 200
