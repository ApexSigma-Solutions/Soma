"""
Tests for ObsidianNeo4jSync connection recovery.

Validates that the module gracefully handles Neo4j unavailability,
supports mock mode for testing, and reports connection status.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from omega_kg.obsidian_sync import ObsidianNeo4jSync, ConnectionError
from neo4j.exceptions import ServiceUnavailable, AuthError


class TestObsidianSyncMockMode:
    """Test mock mode initialization and fallback behavior."""

    def test_obsidian_sync_mock_mode_init(self):
        """Initialize in mock mode should skip connection."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        assert sync.mock_mode is True
        assert sync.driver is None

    @patch("omega_kg.obsidian_sync.settings")
    def test_obsidian_sync_connection_unavailable_fallback(self, mock_settings):
        """Should fall back to mock mode when Neo4j unavailable."""
        mock_settings.neo4j_uri = "bolt://localhost:7688"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/vault"

        with patch("omega_kg.obsidian_sync.GraphDatabase") as mock_gdb:
            mock_gdb.driver.side_effect = ServiceUnavailable("Connection refused")

            sync = ObsidianNeo4jSync(mock_mode=False)

            assert sync.mock_mode is True
            assert sync.driver is None

    @patch("omega_kg.obsidian_sync.settings")
    def test_obsidian_sync_auth_error_fallback(self, mock_settings):
        """Should fall back to mock mode on authentication error."""
        mock_settings.neo4j_uri = "bolt://localhost:7688"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/vault"

        with patch("omega_kg.obsidian_sync.GraphDatabase") as mock_gdb:
            mock_gdb.driver.side_effect = AuthError("Invalid credentials")

            sync = ObsidianNeo4jSync(mock_mode=False)

            assert sync.mock_mode is True
            assert sync.driver is None


class TestObsidianSyncConnectionStatus:
    """Test connection status reporting."""

    def test_connection_status_mock_mode(self):
        """Should report correct status in mock mode."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        status = sync.get_connection_status()

        assert status["connected"] is False
        assert status["mock_mode"] is True
        assert status["uri"] == "mock://local"

    @patch("omega_kg.obsidian_sync.settings")
    def test_connection_status_connected(self, mock_settings):
        """Should report connected when driver exists."""
        mock_settings.neo4j_uri = "bolt://localhost:7688"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/vault"

        with patch("omega_kg.obsidian_sync.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_gdb.driver.return_value = mock_driver
            mock_session = MagicMock()
            mock_driver.session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

            mock_result = MagicMock()
            mock_result.single.return_value = {"status": 1}
            mock_session.run.return_value = mock_result

            sync = ObsidianNeo4jSync(mock_mode=False)
            status = sync.get_connection_status()

            assert status["connected"] is True
            assert status["mock_mode"] is False
            assert "bolt://" in str(status["uri"])


class TestObsidianSyncOperations:
    """Test sync operations with connection recovery."""

    def test_sync_all_tasks_mock_mode(self, capsys):
        """Should skip sync when in mock mode."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        result = sync.sync_all_tasks()

        assert result == 0
        captured = capsys.readouterr()
        assert "mock mode" in captured.out

    def test_sync_task_note_mock_mode(self, capsys):
        """Should skip single task sync when in mock mode."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        task_file = Path("/vault/Tasks/test.md")
        sync.sync_task_note(task_file)

        captured = capsys.readouterr()
        assert "Mock mode" in captured.out or "mock mode" in captured.out

    def test_get_stale_tasks_mock_mode(self, capsys):
        """Should return empty list when in mock mode."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        result = sync.get_stale_tasks(7)

        assert result == []
        captured = capsys.readouterr()
        assert "mock mode" in captured.out

    def test_get_stale_tasks_no_driver(self, capsys):
        """Should return empty list when in mock mode."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        result = sync.get_stale_tasks(7)

        assert result == []
        captured = capsys.readouterr()
        assert "mock mode" in captured.out

    def test_get_stale_tasks_connection_lost(self, caplog):
        """Should handle connection loss during query."""
        with patch("omega_kg.obsidian_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7688"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "/vault"

            with patch("omega_kg.obsidian_sync.GraphDatabase") as mock_gdb:
                mock_driver = MagicMock()
                mock_gdb.driver.return_value = mock_driver
                mock_session = MagicMock()
                mock_driver.session.return_value.__enter__ = MagicMock(
                    return_value=mock_session
                )
                mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

                # First call (health check) succeeds
                mock_result = MagicMock()
                mock_result.single.return_value = {"status": 1}

                call_count = [0]

                def run_side_effect(query, **kwargs):
                    """
                    Simulate a session.run behavior that returns a successful health-check result once, then raises ServiceUnavailable on subsequent calls.

                    Returns:
                        mock_result: The successful result returned on the first invocation.

                    Raises:
                        ServiceUnavailable: On the second and any later invocation to simulate a lost connection.
                    """
                    call_count[0] += 1
                    if call_count[0] == 1:  # Health check
                        return mock_result
                    else:  # Query call
                        raise ServiceUnavailable("Connection lost")

                mock_session.run.side_effect = run_side_effect

                sync = ObsidianNeo4jSync(mock_mode=False)
                result = sync.get_stale_tasks(7)

                assert result == []
                assert "Could not query stale tasks (connection lost)" in caplog.text


class TestObsidianSyncConnectionCheck:
    """Test connection health checks."""

    @patch("omega_kg.obsidian_sync.settings")
    def test_check_connection_health(self, mock_settings):
        """Should verify connection with test query."""
        mock_settings.neo4j_uri = "bolt://localhost:7688"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/vault"

        with patch("omega_kg.obsidian_sync.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_gdb.driver.return_value = mock_driver
            mock_session = MagicMock()
            mock_driver.session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

            mock_result = MagicMock()
            mock_result.single.return_value = {"status": 1}
            mock_session.run.return_value = mock_result

            sync = ObsidianNeo4jSync(mock_mode=False)
            # Verify driver was set (means connection was successful)
            assert sync.driver is not None

    def test_check_connection_no_driver(self):
        """Should raise ConnectionError if driver is None."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        with pytest.raises(ConnectionError):
            sync._check_connection()

    @patch("omega_kg.obsidian_sync.settings")
    def test_check_connection_query_fails(self, mock_settings):
        """
        Verify that a failed health-check query causes the sync instance to revert to mock mode.

        Sets up a mocked Neo4j driver/session whose health-check query raises an exception and asserts the ObsidianNeo4jSync instance falls back to mock mode.
        """
        mock_settings.neo4j_uri = "bolt://localhost:7688"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/vault"

        with patch("omega_kg.obsidian_sync.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_gdb.driver.return_value = mock_driver
            mock_session = MagicMock()
            mock_driver.session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)
            mock_session.run.side_effect = Exception("Query failed")

            sync = ObsidianNeo4jSync(mock_mode=False)
            # Should fall back to mock mode due to health check failure
            assert sync.mock_mode is True


class TestObsidianSyncCleanup:
    """Test resource cleanup."""

    @patch("omega_kg.obsidian_sync.settings")
    def test_close_with_driver(self, mock_settings):
        """
        Verify that when a Neo4j driver is available, ObsidianNeo4jSync.close() calls the driver's close method once.
        """
        mock_settings.neo4j_uri = "bolt://localhost:7688"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/vault"

        with patch("omega_kg.obsidian_sync.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_gdb.driver.return_value = mock_driver
            mock_session = MagicMock()
            mock_driver.session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

            mock_result = MagicMock()
            mock_result.single.return_value = {"status": 1}
            mock_session.run.return_value = mock_result

            sync = ObsidianNeo4jSync(mock_mode=False)
            sync.close()

            mock_driver.close.assert_called_once()

    def test_close_without_driver(self):
        """Should handle close gracefully when driver is None."""
        sync = ObsidianNeo4jSync(mock_mode=True)
        sync.close()  # Should not raise

        assert sync.driver is None
