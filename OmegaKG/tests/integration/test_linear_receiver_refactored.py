"""
Integration tests for Linear Receiver refactoring (TN-102)

Tests end-to-end webhook flow, latency, and backward compatibility.
"""

import hmac
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from omega_kg.main import app
from omega_kg.models import Base, RawLinearEvent, RawWebhookEvent
from omega_kg.domain.linear.processor import process_pending_events
from omega_kg.database.session import engine, AsyncSessionLocal


@pytest.fixture
async def async_db_session():
    """Create async database session for testing."""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with AsyncSessionLocal() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all(bind=engine))


@pytest.fixture
def test_vault(tmp_path: Path) -> Path:
    """Create temporary test vault directory."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    return vault_path


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def linear_webhook_secret():
    """Get Linear webhook secret from settings."""
    from omega_kg.settings import settings

    return settings.linear_webhook_secret


@pytest.fixture
def sample_linear_payload():
    """Sample Linear webhook payload."""
    return {
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


def generate_linear_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate HMAC signature for Linear webhook."""
    signature = hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()
    return signature


class TestWebhookEndpoint:
    """Test refactored webhook endpoint."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_webhook_flow(
        self,
        test_client,
        async_db_session,
        sample_linear_payload,
        linear_webhook_secret,
        test_vault,
    ):
        """Test: Webhook → DB → Processing flow."""
        # Generate payload bytes and signature
        payload_bytes = json.dumps(sample_linear_payload).encode("utf-8")
        signature = generate_linear_signature(payload_bytes, linear_webhook_secret)

        # Send webhook
        response = test_client.post(
            "/webhooks/linear",
            content=payload_bytes,
            headers={"Linear-Signature": signature},
        )

        # Verify response
        assert response.status_code == 200
        assert response.json()["status"] == "persisted"
        event_id = response.json()["id"]

        # Verify event in database
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await async_db_session.execute(query)
        event = result.scalar_one()

        assert event.source == "linear"
        assert event.processed_status is False
        assert isinstance(event.payload, bytes)

        # Process events
        stats = await process_pending_events(async_db_session, test_vault)

        # Verify processing
        assert stats["processed"] == 1
        assert stats["errors"] == 0

        # Verify event marked as processed
        await async_db_session.refresh(event)
        assert event.processed_status is True

        # Verify markdown file created
        markdown_file = test_vault / "Linear" / "[APX-123] Test Issue.md"
        assert markdown_file.exists()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_latency_under_200ms(
        self,
        test_client,
        sample_linear_payload,
        linear_webhook_secret,
    ):
        """Test: Endpoint responds within 200ms."""
        # Generate payload bytes and signature
        payload_bytes = json.dumps(sample_linear_payload).encode("utf-8")
        signature = generate_linear_signature(payload_bytes, linear_webhook_secret)

        # Measure latency
        start_time = time.time()
        response = test_client.post(
            "/webhooks/linear",
            content=payload_bytes,
            headers={"Linear-Signature": signature},
        )
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000

        # Verify response
        assert response.status_code == 200

        # Verify latency < 200ms
        assert latency_ms < 200, f"Latency {latency_ms}ms exceeds 200ms threshold"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_raw_payload_byte_for_byte(
        self,
        test_client,
        async_db_session,
        sample_linear_payload,
        linear_webhook_secret,
    ):
        """Test: Raw payload is saved byte-for-byte."""
        # Generate payload bytes and signature
        payload_bytes = json.dumps(sample_linear_payload).encode("utf-8")
        signature = generate_linear_signature(payload_bytes, linear_webhook_secret)

        # Send webhook
        response = test_client.post(
            "/webhooks/linear",
            content=payload_bytes,
            headers={"Linear-Signature": signature},
        )

        # Verify response
        assert response.status_code == 200
        event_id = response.json()["id"]

        # Retrieve event from database
        query = select(RawWebhookEvent).where(RawWebhookEvent.id == event_id)
        result = await async_db_session.execute(query)
        event = result.scalar_one()

        # Verify byte-for-byte comparison
        original_bytes = json.dumps(sample_linear_payload).encode("utf-8")
        assert event.payload == original_bytes

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_events_processed_sequentially(
        self,
        test_client,
        async_db_session,
        linear_webhook_secret,
        test_vault,
    ):
        """Test: Multiple events processed sequentially."""
        # Create multiple payloads
        payloads = [
            {
                "type": "Issue",
                "action": "create",
                "data": {
                    "id": f"test-issue-{i}",
                    "identifier": f"APX-{i}",
                    "title": f"Test Issue {i}",
                    "description": f"<p>Description {i}</p>",
                    "priority": 2,
                    "state": {
                        "id": "state-id",
                        "name": "In Progress",
                        "type": "started",
                    },
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                },
            }
            for i in range(3)
        ]

        # Send multiple webhooks
        event_ids = []
        for payload in payloads:
            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = generate_linear_signature(payload_bytes, linear_webhook_secret)
            response = test_client.post(
                "/webhooks/linear",
                content=payload_bytes,
                headers={"Linear-Signature": signature},
            )
            assert response.status_code == 200
            event_ids.append(response.json()["id"])

        # Process all events
        stats = await process_pending_events(async_db_session, test_vault)

        # Verify all processed
        assert stats["processed"] == 3
        assert stats["errors"] == 0

        # Verify all markdown files created
        for i in range(3):
            markdown_file = test_vault / "Linear" / f"[APX-{i}] Test Issue {i}.md"
            assert markdown_file.exists()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(
        self,
        test_client,
        sample_linear_payload,
    ):
        """Test: Invalid signature is rejected with 401."""
        # Send webhook with invalid signature
        response = test_client.post(
            "/webhooks/linear",
            json=sample_linear_payload,
            headers={"Linear-Signature": "invalid-signature"},
        )

        # Verify 401 response
        assert response.status_code == 401
        assert "Invalid Signature" in response.json()["detail"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_backward_compatibility(
        self,
        async_db_session,
        test_vault,
    ):
        """Test: Old RawLinearEvent records still process correctly."""
        # Create old-style event in RawLinearEvent
        old_event = RawLinearEvent(
            signature="test-signature",
            event_type="Issue",
            action="create",
            headers={"content-type": "application/json"},
            body={
                "type": "Issue",
                "action": "create",
                "data": {
                    "id": "old-issue-id",
                    "identifier": "OLD-123",
                    "title": "Old Issue",
                    "description": "<p>Old description</p>",
                    "priority": 2,
                    "state": {
                        "id": "state-id",
                        "name": "In Progress",
                        "type": "started",
                        "color": "#ff0000",
                    },
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                },
            },
            processed=False,
        )

        async_db_session.add(old_event)
        await async_db_session.commit()

        # Process events
        stats = await process_pending_events(async_db_session, test_vault)

        # Verify old event processed
        assert stats["processed"] == 1
        assert stats["errors"] == 0

        # Verify markdown file created
        markdown_file = test_vault / "Linear" / "[OLD-123] Old Issue.md"
        assert markdown_file.exists()

        # Verify event marked as processed
        await async_db_session.refresh(old_event)
        assert old_event.processed is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mixed_old_and_new_events(
        self,
        test_client,
        async_db_session,
        linear_webhook_secret,
        test_vault,
    ):
        """Test: Both old and new events processed together."""
        # Create old-style event
        old_event = RawLinearEvent(
            signature="test-signature",
            event_type="Issue",
            action="create",
            headers={"content-type": "application/json"},
            body={
                "type": "Issue",
                "action": "create",
                "data": {
                    "id": "old-issue-id",
                    "identifier": "OLD-123",
                    "title": "Old Issue",
                    "description": "<p>Old description</p>",
                    "priority": 2,
                    "state": {
                        "id": "state-id",
                        "name": "In Progress",
                        "type": "started",
                    },
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                },
            },
            processed=False,
        )

        async_db_session.add(old_event)
        await async_db_session.commit()

        # Send new-style webhook
        new_payload = {
            "type": "Issue",
            "action": "create",
            "data": {
                "id": "new-issue-id",
                "identifier": "NEW-456",
                "title": "New Issue",
                "description": "<p>New description</p>",
                "priority": 2,
                "state": {
                    "id": "state-id",
                    "name": "In Progress",
                    "type": "started",
                    "color": "#ff0000",
                },
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
        }

        payload_bytes = json.dumps(new_payload).encode("utf-8")
        signature = generate_linear_signature(payload_bytes, linear_webhook_secret)
        response = test_client.post(
            "/webhooks/linear",
            content=payload_bytes,
            headers={"Linear-Signature": signature},
        )

        assert response.status_code == 200

        # Process all events
        stats = await process_pending_events(async_db_session, test_vault)

        # Verify both processed
        assert stats["processed"] == 2
        assert stats["errors"] == 0

        # Verify both markdown files created
        old_file = test_vault / "Linear" / "[OLD-123] Old Issue.md"
        new_file = test_vault / "Linear" / "[NEW-456] New Issue.md"
        assert old_file.exists()
        assert new_file.exists()
