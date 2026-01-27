"""
Unit tests for Linear Receiver refactoring (TN-102)

Updated to match current implementation in omega_kg.routers.linear_receiver:
- Uses RawLinearEvent
- Parses JSON body and stores parsed dict in `body`
- Stores `processed` boolean (not processed_status)
- Imports json in module (parsing is expected)
- Extracts external_timestamp if valid ISO8601 string present
"""

import hmac
import hashlib
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.routers.linear_receiver import verify_signature, receive_linear_event
from omega_kg.settings import settings


@pytest.fixture
def mock_request():
    request = Mock()
    request.headers = {}
    request.body = AsyncMock()
    return request


@pytest.fixture
def test_payload():
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
            "createdAt": "2020-01-01T00:00:00.000Z",
            "updatedAt": "2020-01-01T00:00:00.000Z",
        },
    }


@pytest.fixture
def generate_signature(test_payload):
    secret = settings.linear_webhook_secret
    payload_bytes = json.dumps(test_payload).encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()
    return payload_bytes, signature


class TestSignatureVerification:
    @pytest.mark.asyncio
    async def test_verify_signature_valid(self, mock_request, generate_signature):
        payload_bytes, signature = generate_signature
        mock_request.headers = {"Linear-Signature": signature}
        mock_request.body.return_value = payload_bytes

        result = await verify_signature(mock_request)
        assert result == (payload_bytes, signature)

    @pytest.mark.asyncio
    async def test_verify_signature_invalid(self, mock_request, generate_signature):
        payload_bytes, _ = generate_signature
        mock_request.headers = {"Linear-Signature": "invalid-signature"}
        mock_request.body.return_value = payload_bytes

        with pytest.raises(HTTPException) as exc_info:
            await verify_signature(mock_request)
        assert exc_info.value.status_code == 401
        assert "Invalid Signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_signature_missing(self, mock_request, generate_signature):
        payload_bytes, _ = generate_signature
        mock_request.headers = {}
        mock_request.body.return_value = payload_bytes

        with pytest.raises(HTTPException) as exc_info:
            await verify_signature(mock_request)
        assert exc_info.value.status_code == 400
        assert "Missing Linear-Signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_signature_alternate_header(
        self, mock_request, generate_signature
    ):
        payload_bytes, signature = generate_signature
        mock_request.headers = {"X-Linear-Signature": signature}
        mock_request.body.return_value = payload_bytes

        result = await verify_signature(mock_request)
        assert result == (payload_bytes, signature)


class TestReceiveLinearEvent:
    @pytest.mark.asyncio
    async def test_receive_event_persists_parsed_payload(
        self, mock_request, generate_signature, test_payload
    ):
        payload_bytes, signature = generate_signature
        mock_request.headers = {"Linear-Signature": signature}
        mock_request.body.return_value = payload_bytes

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()

        mock_event = Mock()
        mock_event.id = 1

        with patch(
            "omega_kg.routers.linear_receiver.RawLinearEvent", return_value=mock_event
        ) as mock_constructor:
            result = await receive_linear_event(
                request=mock_request,
                db=mock_db,
                verification=(payload_bytes, signature),
            )

        mock_db.add.assert_called_once_with(mock_event)
        mock_db.commit.assert_called_once()

        assert result["status"] == "persisted"
        assert result["id"] == 1

        # Verify RawLinearEvent constructor kwargs
        call_kwargs = mock_constructor.call_args[1]
        assert call_kwargs["signature"] == signature
        assert call_kwargs["event_type"] == test_payload["type"]
        assert call_kwargs["action"] == test_payload["action"]
        assert call_kwargs["headers"] == dict(mock_request.headers)
        assert call_kwargs["body"] == json.loads(payload_bytes)
        assert call_kwargs["processed"] is False

    @pytest.mark.asyncio
    async def test_receive_event_parses_external_timestamp(
        self, mock_request, test_payload
    ):
        # Ensure createdAt is parsed into a timezone-aware datetime
        payload = dict(test_payload)
        payload["data"] = dict(test_payload["data"])
        payload["data"]["createdAt"] = "2020-01-01T00:00:00.000Z"
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            settings.linear_webhook_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        mock_request.headers = {"Linear-Signature": signature}
        mock_request.body.return_value = payload_bytes

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()

        mock_event = Mock()
        mock_event.id = 2

        with patch(
            "omega_kg.routers.linear_receiver.RawLinearEvent", return_value=mock_event
        ) as mock_constructor:
            await receive_linear_event(
                request=mock_request,
                db=mock_db,
                verification=(payload_bytes, signature),
            )

        call_kwargs = mock_constructor.call_args[1]
        ext_ts = call_kwargs["external_timestamp"]
        assert isinstance(ext_ts, datetime)
        # Normalize to UTC for comparison
        assert (
            ext_ts.astimezone(timezone.utc)
            .isoformat()
            .startswith("2020-01-01T00:00:00")
        )

    @pytest.mark.asyncio
    async def test_receive_event_handles_invalid_timestamp_gracefully(
        self, mock_request, test_payload
    ):
        payload = dict(test_payload)
        payload["data"] = dict(test_payload["data"])
        payload["data"]["createdAt"] = "not-a-timestamp"
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            settings.linear_webhook_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        mock_request.headers = {"Linear-Signature": signature}
        mock_request.body.return_value = payload_bytes

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()

        mock_event = Mock()
        mock_event.id = 3

        with patch(
            "omega_kg.routers.linear_receiver.RawLinearEvent", return_value=mock_event
        ) as mock_constructor:
            await receive_linear_event(
                request=mock_request,
                db=mock_db,
                verification=(payload_bytes, signature),
            )

        call_kwargs = mock_constructor.call_args[1]
        assert call_kwargs["external_timestamp"] is None

    @pytest.mark.asyncio
    async def test_receive_event_stores_parsed_body_not_bytes(
        self, mock_request, generate_signature
    ):
        payload_bytes, signature = generate_signature
        mock_request.headers = {"Linear-Signature": signature}
        mock_request.body.return_value = payload_bytes

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()

        mock_event = Mock()
        mock_event.id = 4

        with patch(
            "omega_kg.routers.linear_receiver.RawLinearEvent", return_value=mock_event
        ) as mock_constructor:
            await receive_linear_event(
                request=mock_request,
                db=mock_db,
                verification=(payload_bytes, signature),
            )

        call_kwargs = mock_constructor.call_args[1]
        assert isinstance(call_kwargs["body"], dict)
        assert call_kwargs["body"] == json.loads(payload_bytes)

    @pytest.mark.asyncio
    async def test_receive_event_persistence_failure_returns_500(
        self, mock_request, generate_signature
    ):
        payload_bytes, signature = generate_signature
        mock_request.headers = {"Linear-Signature": signature}
        mock_request.body.return_value = payload_bytes

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock(side_effect=Exception("boom"))

        mock_event = Mock()

        with patch(
            "omega_kg.routers.linear_receiver.RawLinearEvent", return_value=mock_event
        ):
            with pytest.raises(HTTPException) as exc_info:
                await receive_linear_event(
                    request=mock_request,
                    db=mock_db,
                    verification=(payload_bytes, signature),
                )

        assert exc_info.value.status_code == 500
        assert "Persistence Failure" in exc_info.value.detail

    def test_module_imports_json(self):
        # The implementation expects JSON parsing; json should be imported
        import omega_kg.routers.linear_receiver as receiver_module

        assert "json" in receiver_module.__dict__
