import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime

from omega_kg.capture_server import app
from omega_kg.models.terminal import TerminalEvent


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_terminal_event_pipeline_refactor():
    """
    Integration test for TN-CORE-104:
    1. Capture endpoint writes to raw_terminal_events
    2. SagaWeaver polls and calls Validation API
    3. SagaWeaver marks as processed
    """

    # 1. Mock external services and internal storage
    # Mock embedding generation to avoid Ollama dependency
    with (
        patch(
            "omega_kg.workers.embedding_worker.generate_embedding",
            new_callable=AsyncMock,
        ) as mock_embed,
        patch(
            "omega_kg.services.omegakg_client.OmegaKGInternalClient.validate_and_store",
            new_callable=AsyncMock,
        ) as mock_api,
        patch("omega_kg.services.neo4j_adapter.Neo4jAdapter", autospec=True),
        patch("omega_kg.capture_server.get_vector_store", new_callable=AsyncMock),
        patch(
            "omega_kg.capture_server._start_ollama", new_callable=AsyncMock
        ) as mock_ollama,
        patch("omega_kg.vault_utils.VaultUtils", autospec=True),
        patch(
            "omega_kg.routers.terminal.process_terminal_event_background",
            new_callable=AsyncMock,
        ),
        patch("omega_kg.capture_server.start_worker", new_callable=AsyncMock),
    ):
        mock_ollama.return_value = True
        mock_embed.return_value = [0.1] * 1024
        mock_api.return_value = {
            "status": "accepted",
            "message": "Validated and stored",
            "neo4j_node_id": "node_123",
            "vector_id": 456,
            "source_id": "test-event-id",
            "digest_type": "terminal_event",
        }

        # 2. Test Capture Endpoint
        test_payload = {
            "command": "git status",
            "cwd": "/home/user",
            "exit_code": 0,
            "output": "On branch main",
            "user": "testuser",
            "host": "testhost",
            "session_id": "test-session-123",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # We need to use AsyncClient for the app or TestClient if we don't care about async db in the endpoint
        # But wait, the endpoint uses AsyncSession. TestClient handles this if we use the right dependency overrides.

        from httpx import AsyncClient, ASGITransport

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post("/capture/terminal/", json=test_payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "captured"
            event_id = data["event_id"]
            assert event_id is not None

            # 3. Verify Raw Persistence
            from omega_kg.database import get_ingest_session

            async with get_ingest_session() as session:
                from sqlalchemy import select

                stmt = select(TerminalEvent).where(TerminalEvent.event_id == event_id)
                result = await session.execute(stmt)
                event = result.scalar_one_or_none()

                assert event is not None
                assert event.command == "git status"
                assert event.processed is False
                assert event.raw_payload["command"] == "git status"
                assert event.captured_at is not None

            # 4. Trigger SagaWeaver
            from omega_kg.workers.embedding_worker import SagaWeaver

            weaver = SagaWeaver()
            # Mocking poll interval or just calling process once
            await weaver.process_terminal_queue()

            # 5. Verify API Call
            mock_api.assert_awaited_once()
            args, kwargs = mock_api.call_args
            digest = args[0]
            assert digest.source_id == str(event_id)
            assert "git status" in digest.content
            assert digest.metadata["session_id"] == "test-session-123"

            # 6. Verify Processed Status
            async with get_ingest_session() as session:
                result = await session.execute(stmt)
                event = result.scalar_one_or_none()
                assert event.processed is True
                assert event.processed_at is not None
                assert event.last_error is None


if __name__ == "__main__":
    # This is for manual run

    pytest.main([__file__])
