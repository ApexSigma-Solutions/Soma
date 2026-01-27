"""
Unit tests for cli.py
"""

from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from omega_kg.cli import cli


class TestCLI:
    """Test suite for CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("omega_kg.cli.KnowledgeGraphSchema")
    def test_init_command(self, mock_schema_class):
        """Test the init command."""
        mock_schema = Mock()
        mock_schema_class.return_value = mock_schema

        result = self.runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "🔧 Initializing Neo4j schema..." in result.output
        assert "✓ Schema initialized" in result.output

        # Verify schema methods were called
        mock_schema.initialize_schema.assert_called_once()
        mock_schema.create_sample_relationships.assert_called_once()
        mock_schema.close.assert_called_once()

    @patch("omega_kg.cli.TaskLifecycle")
    def test_lifecycle_command_dry_run(self, mock_lifecycle_class):
        """Test the lifecycle command with dry-run flag."""
        mock_lc = Mock()
        mock_report = "Test lifecycle report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ["lifecycle", "--dry-run"])

        assert result.exit_code == 0
        assert "🔄 Running lifecycle enforcement..." in result.output
        assert mock_report in result.output

        # Verify lifecycle methods were called correctly
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=True)
        mock_lc.generate_report.assert_called_once()
        mock_lc.send_email_report.assert_not_called()
        mock_lc.close.assert_called_once()

    @patch("omega_kg.cli.TaskLifecycle")
    def test_lifecycle_command_with_email(self, mock_lifecycle_class):
        """Test the lifecycle command with email sending."""
        mock_lc = Mock()
        mock_report = "Test lifecycle report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ["lifecycle"])

        assert result.exit_code == 0
        assert mock_report in result.output

        # Verify email was sent
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=False)
        mock_lc.send_email_report.assert_called_once_with(mock_report)

    @patch("omega_kg.obsidian_sync.ObsidianNeo4jSync")
    @patch("neo4j.GraphDatabase")
    @patch("omega_kg.settings")
    def test_stats_command_connected(
        self, mock_settings, mock_graph_db, mock_sync_class
    ):
        """Test the stats command when connected to Neo4j."""
        # Mock sync
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": True}
        mock_sync_class.return_value = mock_sync

        # Mock Neo4j driver and session
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        # Mock query result
        mock_result = Mock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(
            side_effect=lambda key: {
                "total": 10,
                "draft": 3,
                "active": 4,
                "completed": 2,
                "archived": 1,
            }.get(key, 0)
        )
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        result = self.runner.invoke(cli, ["stats"])

        assert result.exit_code == 0
        assert "✓ Neo4j connection established" in result.output
        assert "📊 Knowledge Graph Statistics" in result.output
        assert "Total Tasks:      10" in result.output
        assert "Draft:            3" in result.output
        assert "Active:           4" in result.output
        assert "Completed:        2" in result.output
        assert "Archived:         1" in result.output

        mock_sync.close.assert_called_once()

    @patch("omega_kg.obsidian_sync.ObsidianNeo4jSync")
    def test_stats_command_mock_mode(self, mock_sync_class):
        """Test the stats command in mock mode."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": False}
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ["stats"])

        assert result.exit_code == 0
        assert "[WARN] Running in mock mode" in result.output
        mock_sync.close.assert_called_once()

    @patch("omega_kg.obsidian_sync.ObsidianNeo4jSync")
    def test_stale_command(self, mock_sync_class):
        """Test the stale command."""
        mock_sync = Mock()
        mock_stale_tasks = [
            {"t.uid": "TASK-001", "t.title": "Old Task", "t.created": "2023-01-01"}
        ]
        mock_sync.get_stale_tasks.return_value = mock_stale_tasks
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ["stale"])

        assert result.exit_code == 0
        assert "--- Stale Tasks (>7 days) ---" in result.output
        assert "TASK-001: Old Task" in result.output
        mock_sync.get_stale_tasks.assert_called_once_with(7)
        mock_sync.close.assert_called_once()

    @patch("omega_kg.obsidian_sync.ObsidianNeo4jSync")
    def test_stale_command_no_stale_tasks(self, mock_sync_class):
        """Test the stale command when no stale tasks exist."""
        mock_sync = Mock()
        mock_sync.get_stale_tasks.return_value = []
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ["stale"])

        assert result.exit_code == 0
        assert "(none)" in result.output
        mock_sync.close.assert_called_once()

    @patch("omega_kg.obsidian_sync.ObsidianNeo4jSync")
    def test_sync_command(self, mock_sync_class):
        """Test the sync command."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {
            "connected": True,
            "uri": "bolt://localhost:7687",
        }
        mock_sync.sync_all_tasks.return_value = 5
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "🔄 Syncing Obsidian vault to Neo4j..." in result.output
        assert "✓ Connected to Neo4j: bolt://localhost:7687" in result.output
        assert "✓ Synced 5 tasks" in result.output
        mock_sync.sync_all_tasks.assert_called_once()
        mock_sync.close.assert_called_once()

    @patch("omega_kg.obsidian_sync.ObsidianNeo4jSync")
    def test_sync_command_mock_mode(self, mock_sync_class):
        """Test the sync command with --mock flag."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {
            "connected": False,
            "uri": "mock://local",
        }
        mock_sync.sync_all_tasks.return_value = 0
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ["sync", "--mock"])

        assert result.exit_code == 0
        assert "⚠ Running in mock mode" in result.output
        mock_sync_class.assert_called_once_with(mock_mode=True)
        mock_sync.close.assert_called_once()

    @patch("omega_kg.lifecycle.GraphDatabase.driver")
    def test_status_command(self, mock_driver_class, monkeypatch):
        """Test the status command."""
        # Set environment variables for settings
        monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
        monkeypatch.setenv("NEO4J_USER", "neo4j")
        monkeypatch.setenv("NEO4J_PASSWORD", "password")
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "./vault")
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USER", "test@example.com")
        monkeypatch.setenv("EMAIL_TO", "recipient@example.com")
        monkeypatch.setenv("LINEAR_API_KEY", "test-api-key")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-123")

        # Mock driver and session for successful connection
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_session.run.return_value.single.return_value = {"status": 1}
        mock_driver_class.return_value = mock_driver

        result = self.runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "🔍 System Status Check" in result.output
        assert "bolt://localhost:7687" in result.output
        assert "✓ Yes" in result.output
        assert "development" in result.output

    @patch("omega_kg.settings.settings")
    @patch("omega_kg.lifecycle.settings")
    def test_status_command_mock_mode(
        self, mock_lifecycle_settings, mock_cli_settings, monkeypatch
    ):
        """Test the status command in mock mode."""
        # Mock settings to return invalid Neo4j config to force mock mode
        mock_lifecycle_settings.neo4j_uri = "bolt://invalid:9999"
        mock_lifecycle_settings.neo4j_user = "invalid"
        mock_lifecycle_settings.neo4j_password = "invalid"
        mock_lifecycle_settings.obsidian_vault_path = "./vault"
        mock_lifecycle_settings.app_env = "test"

        mock_cli_settings.neo4j_uri = "bolt://invalid:9999"
        mock_cli_settings.neo4j_user = "invalid"
        mock_cli_settings.neo4j_password = "invalid"
        mock_cli_settings.obsidian_vault_path = "./vault"
        mock_cli_settings.app_env = "test"

        # Mock email settings to None to show as not configured
        mock_cli_settings.smtp_host = None
        mock_cli_settings.smtp_user = None
        mock_cli_settings.email_to = None
        mock_cli_settings.linear_api_key = None

        result = self.runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "mock://local" in result.output
        assert "✗ No" in result.output
        assert "✗ Not configured" in result.output

    @patch("omega_kg.cli.TaskLifecycle")
    def test_report_command(self, mock_lifecycle_class):
        """Test the report command."""
        mock_lc = Mock()
        mock_lc.get_connection_status.return_value = {
            "connected": True,
            "uri": "bolt://localhost:7687",
        }
        mock_report = "Test report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ["report"])

        assert result.exit_code == 0
        assert "📊 Generating lifecycle report..." in result.output
        assert mock_report in result.output
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=True)
        mock_lc.send_email_report.assert_not_called()
        mock_lc.close.assert_called_once()

    @patch("omega_kg.cli.TaskLifecycle")
    def test_report_command_with_email(self, mock_lifecycle_class):
        """Test the report command with --email flag."""
        mock_lc = Mock()
        mock_lc.get_connection_status.return_value = {
            "connected": True,
            "uri": "bolt://localhost:7687",
        }
        mock_report = "Test report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ["report", "--email"])

        assert result.exit_code == 0
        mock_lc.send_email_report.assert_called_once_with(mock_report)
