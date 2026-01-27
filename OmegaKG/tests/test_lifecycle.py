"""
Unit tests for omega_kg.lifecycle module
"""

from unittest.mock import patch
from omega_kg.lifecycle import TaskStatus, LifecycleRule, TaskLifecycle


class TestTaskStatus:
    """Test the TaskStatus enum"""

    def test_task_status_values(self):
        """Test that TaskStatus enum has all required states"""
        assert TaskStatus.DRAFT.value == "draft"
        assert TaskStatus.READY.value == "ready"
        assert TaskStatus.ACTIVE.value == "active"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.ARCHIVED.value == "archived"

    def test_task_status_enum_length(self):
        """Test that TaskStatus has exactly 6 states"""
        assert len(TaskStatus) == 6


class TestLifecycleRule:
    """Test the LifecycleRule dataclass"""

    def test_lifecycle_rule_creation(self, sample_lifecycle_rule_data):
        """Test creating a LifecycleRule"""
        rule = LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=14,
            condition="NOT t.pinned = true",
            action="auto",
        )

        assert rule.from_status == TaskStatus.DRAFT
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 14
        assert rule.condition == "NOT t.pinned = true"
        assert rule.action == "auto"

    def test_lifecycle_rule_default_action(self):
        """Test that LifecycleRule has default action"""
        rule = LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=14,
        )

        assert rule.action == "auto"


class TestTaskLifecycle:
    """Test the TaskLifecycle class"""

    def test_task_lifecycle_initialization(self, mock_neo4j_driver):
        """
        Verify TaskLifecycle initializes a Neo4j driver and exposes the configured vault path name.

        Patches the Neo4j driver and settings to instantiate TaskLifecycle, then asserts a driver is assigned and the vault path's name equals "vault".

        Parameters:
            mock_neo4j_driver: A mock object provided as the Neo4j driver replacement.
        """
        with patch(
            "omega_kg.lifecycle.GraphDatabase.driver", return_value=mock_neo4j_driver
        ):
            with patch("omega_kg.lifecycle.settings") as mock_settings:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = "./vault"

                lifecycle = TaskLifecycle()

                assert lifecycle.driver is not None
                assert lifecycle.vault_path.name == "vault"

    def test_lifecycle_rules_defined(self):
        """Test that TaskLifecycle has rules defined"""
        assert len(TaskLifecycle.RULES) > 0
        assert all(isinstance(rule, LifecycleRule) for rule in TaskLifecycle.RULES)

    def test_first_rule_draft_archival(self):
        """Test the first rule (draft decay to archive)"""
        rule = TaskLifecycle.RULES[0]

        assert rule.from_status == TaskStatus.DRAFT
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 14
        assert rule.action == "auto"

    def test_second_rule_draft_warning(self):
        """Test the second rule (draft warning before archival)"""
        rule = TaskLifecycle.RULES[1]

        assert rule.from_status == TaskStatus.DRAFT
        assert rule.action == "warn"
        assert rule.days_threshold == 10

    def test_third_rule_active_stale(self):
        """Test the third rule (active tasks stale detection)"""
        rule = TaskLifecycle.RULES[2]

        assert rule.from_status == TaskStatus.ACTIVE
        assert rule.to_status == TaskStatus.BLOCKED
        assert rule.days_threshold == 30
        assert rule.action == "warn"

    def test_fourth_rule_completed_archival(self):
        """Test the fourth rule (completed archival)"""
        rule = TaskLifecycle.RULES[3]

        assert rule.from_status == TaskStatus.COMPLETED
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 90
        assert rule.action == "auto"


class TestTaskLifecycleEnforcement:
    """Test TaskLifecycle enforcement methods"""

    @patch("omega_kg.lifecycle.GraphDatabase.driver")
    def test_enforce_lifecycle_dry_run(self, mock_driver_class, mock_neo4j_driver):
        """Test enforce_lifecycle with dry_run=True"""
        mock_driver_class.return_value = mock_neo4j_driver

        with patch("omega_kg.lifecycle.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            lifecycle = TaskLifecycle()
            results = lifecycle.enforce_lifecycle(dry_run=True)

            assert isinstance(results, dict)
            assert "archived" in results
            assert "warned" in results
            assert "blocked" in results
            assert "failed" in results

    @patch("omega_kg.lifecycle.GraphDatabase.driver")
    def test_enforce_lifecycle_returns_dict(self, mock_driver_class, mock_neo4j_driver):
        """Test that enforce_lifecycle returns expected dictionary structure"""
        mock_driver_class.return_value = mock_neo4j_driver

        with patch("omega_kg.lifecycle.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            lifecycle = TaskLifecycle()
            results = lifecycle.enforce_lifecycle(dry_run=True)

            assert isinstance(results, dict)
            assert all(isinstance(v, list) for v in results.values())


class TestTaskLifecycleMockMode:
    """Test TaskLifecycle with mock mode (no database connection)"""

    def test_task_lifecycle_mock_mode_init(self):
        """Test TaskLifecycle initialization in mock mode"""
        lifecycle = TaskLifecycle(mock_mode=True)

        assert lifecycle.mock_mode is True
        assert lifecycle.driver is None

    def test_task_lifecycle_mock_mode_enforce(self):
        """Test lifecycle enforcement in mock mode returns mock data"""
        lifecycle = TaskLifecycle(mock_mode=True)

        results = lifecycle.enforce_lifecycle(dry_run=True)

        # Should return mock results
        assert isinstance(results, dict)
        assert len(results["archived"]) > 0
        assert len(results["warned"]) > 0

    def test_task_lifecycle_connection_status_mock(self):
        """Test connection status in mock mode"""
        lifecycle = TaskLifecycle(mock_mode=True)

        status = lifecycle.get_connection_status()

        assert status["connected"] is False
        assert status["mock_mode"] is True
        assert status["uri"] == "mock://local"

    def test_task_lifecycle_connection_status_real(self, mock_neo4j_driver):
        """Test connection status with real driver"""
        with patch("omega_kg.lifecycle.GraphDatabase.driver") as mock_driver_class:
            mock_driver_class.return_value = mock_neo4j_driver
            # Configure mock session.run().single() to return a truthy result
            mock_neo4j_driver.session.return_value.run.return_value.single.return_value = {
                "count": 1
            }

            with patch("omega_kg.lifecycle.settings") as mock_settings:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = "./vault"

                lifecycle = TaskLifecycle(mock_mode=False)
                status = lifecycle.get_connection_status()

                assert status["connected"] is True
                assert status["mock_mode"] is False
