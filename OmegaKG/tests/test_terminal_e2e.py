import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from omega_kg.capture_server import app
from omega_kg.routers.terminal import get_ingest_db


@pytest.fixture
def mock_ingest_db():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


from uuid import uuid4


async def override_get_ingest_db():
    mock = AsyncMock()

    def fake_refresh(instance):
        if not instance.id:
            instance.id = uuid4()

    mock.add = MagicMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock(side_effect=fake_refresh)
    yield mock


app.dependency_overrides[get_ingest_db] = override_get_ingest_db


@pytest.mark.asyncio
async def test_terminal_capture_noise():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "command": "cd /tmp",
            "cwd": "/home/user",
            "timestamp": "2024-01-01T12:00:00Z",
            "user": "testuser",
            "host": "localhost",
        }
        response = await client.post("/capture/terminal/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"


@pytest.mark.asyncio
async def test_terminal_capture_valid():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "command": "python script.py",
            "cwd": "/home/user",
            "timestamp": "2024-01-01T12:00:00Z",
            "user": "testuser",
            "host": "localhost",
        }
        response = await client.post("/capture/terminal/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "captured"
        assert "event_id" in data
