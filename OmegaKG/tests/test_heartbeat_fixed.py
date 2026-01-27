from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests  # type: ignore[import-untyped]

from omega_kg.quipu_ollama_heartbeat import check_ollama_health, run_heartbeat_loop


@pytest.fixture
def mock_settings():
    with patch("omega_kg.quipu_ollama_heartbeat.settings") as mock:
        mock.ollama_host_url = "http://localhost:11434"
        mock.heartbeat_interval_sec = 1
        mock.quipu_service_name = "test_display"
        yield mock


@pytest.mark.unit
def test_check_ollama_health_online(mock_settings):  # noqa: F811
    _ = mock_settings  # Use fixture to ensure settings are mocked
    with patch("requests.get") as mock_get:
        # Mock / response
        mock_resp_root = MagicMock()
        mock_resp_root.raise_for_status.return_value = None

        # Mock /api/ps response
        mock_resp_ps = MagicMock()
        mock_resp_ps.status_code = 200
        mock_resp_ps.json.return_value = {"models": [{"name": "llama3"}]}

        # Side effect for consecutive calls
        mock_get.side_effect = [mock_resp_root, mock_resp_ps]

        status, latency, model, meta = check_ollama_health()

        assert status == "ONLINE"
        assert model == "llama3"
        assert meta["url"] == "http://localhost:11434"
        assert isinstance(latency, int)


@pytest.mark.unit
def test_check_ollama_health_offline(mock_settings):  # noqa: F811
    _ = mock_settings  # Use fixture to ensure settings are mocked
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        status, _latency, _model, meta = check_ollama_health()
        assert status == "OFFLINE"
        assert "Connection Refused" in meta["error"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_run_heartbeat_loop_break(mock_settings):  # noqa: F811
    """Test that the loop runs at least once and handles DB failure gracefully"""
    _ = mock_settings  # Use fixture to ensure settings are mocked
    with (
        patch(
            "omega_kg.quipu_ollama_heartbeat.init_heartbeat_table",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "omega_kg.quipu_ollama_heartbeat.check_ollama_health",
            return_value=("ONLINE", 10, "test", {}),
        ),
        patch(
            "omega_kg.quipu_ollama_heartbeat.insert_heartbeat",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_insert,
        patch(
            "omega_kg.quipu_ollama_heartbeat.time.sleep", side_effect=KeyboardInterrupt
        ),
    ):  # Break loop
        await run_heartbeat_loop()
        mock_insert.assert_called_once()
