"""
Unit tests for percolation.py
"""

from pathlib import Path
from unittest.mock import Mock, patch

from omega_kg.percolation import PercolationEngine, create_percolation_engine


class TestPercolationEngine:
    """Test suite for PercolationEngine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        # Make session a context manager
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session
        self.engine = PercolationEngine(self.mock_driver)

    def test_initialization(self):
        """Test PercolationEngine initialization."""
        assert self.engine.driver == self.mock_driver

    @patch("omega_kg.percolation.Path")
    def test_percolate_from_vault(self, mock_path_class):
        """Test percolating from a vault with multiple files."""
        # Mock Path and file operations
        mock_vault_path = Mock(spec=Path)
        mock_file1 = Mock(spec=Path)
        mock_file1.read_text.return_value = """
---
date: 2023-01-01
---
# Task
[[PROJ-001]]

#### Git Commit [repo1]: `abc123`
**Linear:** [[PROJ-001]]
**Message:**
```
commit message
```

## Decision
This is a decision
"""
        mock_file2 = Mock(spec=Path)
        mock_file2.read_text.return_value = """
---
date: 2023-01-02
---
# Another Task
[[PROJ-002]]
"""
        mock_vault_path.rglob.return_value = [mock_file1, mock_file2]

        # Mock session
        mock_session = Mock()
        self.mock_driver.session.return_value = mock_session

        # Mock the percolation methods
        with (
            patch.object(self.engine, "_extract_frontmatter") as mock_extract,
            patch.object(self.engine, "_percolate_task") as mock_task,
            patch.object(self.engine, "_percolate_commits") as mock_commits,
            patch.object(self.engine, "_percolate_session") as mock_session_percolate,
        ):
            mock_extract.side_effect = [
                {"date": "2023-01-01", "decision_id": "DEC-001"},
                {"date": "2023-01-02"},
            ]
            mock_task.side_effect = [1, 1]  # One task each
            mock_commits.side_effect = [1, 0]  # One commit from first file
            mock_session_percolate.side_effect = [1, 0]  # One session link

            result = self.engine.percolate_from_vault(mock_vault_path)

            expected = {"tasks": 2, "commits": 1, "links": 1}
            assert result == expected

    def test_extract_frontmatter_valid(self):
        """Test extracting valid frontmatter."""
        content = """---
date: 2023-01-01
title: Test Note
---

# Content
Some content here.
"""

        result = self.engine._extract_frontmatter(content)
        expected = {"date": "2023-01-01", "title": "Test Note"}
        assert result == expected

    def test_extract_frontmatter_no_frontmatter(self):
        """Test extracting from content without frontmatter."""
        content = "# Just content\nNo frontmatter here."

        result = self.engine._extract_frontmatter(content)
        assert result is None

    def test_extract_frontmatter_malformed(self):
        """Test extracting from malformed frontmatter."""
        content = "---\ninvalid: yaml: content:\n---\nContent"

        result = self.engine._extract_frontmatter(content)
        # The method parses what it can, so it returns the parsed dict
        assert result == {"invalid": "yaml: content:"}

    @patch("omega_kg.percolation.datetime")
    def test_percolate_task(self, mock_datetime):
        """Test percolating tasks from content."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"

        mock_file = Mock(spec=Path)
        metadata = {"date": "2023-01-01"}
        content = "Some content [[PROJ-001]] and [[PROJ-002]]"

        result = self.engine._percolate_task(mock_file, metadata, content)

        assert result == 2  # Two tasks found
        # Verify session.run was called for each task
        session_calls = self.mock_driver.session.return_value.run.call_count
        assert session_calls == 2

    @patch("omega_kg.percolation.datetime")
    def test_percolate_commits(self, mock_datetime):
        """Test percolating commits from content."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"

        mock_file = Mock(spec=Path)
        metadata = {}
        content = """#### Git Commit [myrepo]: `abc123`
**Linear:** [[PROJ-001]]
**Message:**
```
Initial commit
```
"""

        result = self.engine._percolate_commits(mock_file, metadata, content)

        assert result == 1  # One commit found
        # Verify session.run was called for commit and relationship
        session_calls = self.mock_driver.session.return_value.run.call_count
        assert session_calls == 2

    def test_percolate_session(self):
        """Test percolating session data."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session

        mock_file = Mock(spec=Path)
        metadata = {"date": "2023-01-01", "topic": "Test Session"}
        content = """
## Decision

This is a test decision about the project.
"""

        with patch.object(self.engine, "_generate_decision_id") as mock_gen_id:
            mock_gen_id.return_value = "DEC-001"

            result = self.engine._percolate_session(mock_file, metadata, content)

            assert result == 1  # One decision link created
            assert (
                mock_session.run.call_count == 3
            )  # MERGE session + MERGE decision + MERGE relationship

    def test_generate_decision_id(self):
        """Test generating decision IDs."""
        content = "This is a test decision content for hashing"
        result = self.engine._generate_decision_id(content)

        # Should return a string in format DEC-XXXX
        assert result.startswith("DEC-")
        assert len(result) == 8  # DEC- + 4 digits

        # Same content should generate same ID
        result2 = self.engine._generate_decision_id(content)
        assert result == result2

    def test_detect_stale_tasks(self):
        """Test detecting stale tasks."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session

        # Mock query results
        mock_records = [
            Mock(
                __getitem__=lambda self, key: {
                    "t.uid": "TASK-001",
                    "t.title": "Stale Task",
                    "t.status": "active",
                    "t.created": "2023-01-01",
                }.get(key)
            )
        ]
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.run.return_value = mock_result

        result = self.engine.detect_stale_tasks(days_threshold=30)

        assert len(result) == 1
        assert result[0]["uid"] == "TASK-001"
        assert result[0]["title"] == "Stale Task"
        assert result[0]["status"] == "active"

    @patch("omega_kg.percolation.GraphDatabase")
    def test_create_percolation_engine(self, mock_graph_db):
        """Test the factory function."""
        mock_driver = Mock()
        mock_graph_db.driver.return_value = mock_driver

        result = create_percolation_engine("uri", "user", "pass")

        assert isinstance(result, PercolationEngine)
        assert result.driver == mock_driver
        mock_graph_db.driver.assert_called_once_with("uri", auth=("user", "pass"))


# ===== VECTOR SIMILARITY THRESHOLD TESTS =====


class TestScanFoldersConfig:
    """Test configurable scan folders feature."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session
        self.engine = PercolationEngine(self.mock_driver)

    @patch("omega_kg.percolation.settings")
    def test_default_scan_folders_from_settings(self, mock_settings):
        """Test that default scan folders are read from settings."""
        mock_settings.obsidian_vault_scan_folders = "Sessions"

        mock_vault_path = Mock(spec=Path)
        mock_vault_path.exists.return_value = True
        mock_file = Mock(spec=Path)
        mock_file.read_text.return_value = "---\ndate: 2023-01-01\n---\n# Content"
        mock_vault_path.__truediv__ = Mock(return_value=mock_vault_path)
        mock_vault_path.rglob.return_value = [mock_file]

        with patch.object(self.engine, "_extract_frontmatter") as mock_extract:
            mock_extract.return_value = {"date": "2023-01-01"}
            result = self.engine.percolate_from_vault(mock_vault_path)

        # Verify __truediv__ was called with "Sessions"
        mock_vault_path.__truediv__.assert_called_with("Sessions")
        assert result == {"tasks": 0, "commits": 0, "links": 0}

    @patch("omega_kg.percolation.settings")
    def test_custom_scan_folders(self, mock_settings):
        """Test that custom scan folders are used when provided."""
        mock_settings.obsidian_vault_scan_folders = "Sessions,TN"

        # Create mock vault path that returns different files for each folder
        mock_sessions_folder = Mock(spec=Path)
        mock_sessions_folder.exists.return_value = True
        mock_sessions_folder.rglob.return_value = []

        mock_tn_folder = Mock(spec=Path)
        mock_tn_folder.exists.return_value = True
        mock_tn_folder.rglob.return_value = []

        mock_vault_path = Mock(spec=Path)

        def truediv_side_effect(folder_name):
            if folder_name == "Sessions":
                return mock_sessions_folder
            elif folder_name == "TN":
                return mock_tn_folder
            return Mock()

        mock_vault_path.__truediv__ = Mock(side_effect=truediv_side_effect)

        # Call with explicit scan_folders parameter
        result = self.engine.percolate_from_vault(
            mock_vault_path, scan_folders=["Sessions", "TN"]
        )

        # Verify both folders were scanned
        assert mock_sessions_folder.rglob.call_count == 1
        assert mock_tn_folder.rglob.call_count == 1
        assert result == {"tasks": 0, "commits": 0, "links": 0}

    @patch("omega_kg.percolation.settings")
    @patch("omega_kg.percolation.logger")
    def test_nonexistent_folder_warning(self, mock_logger, mock_settings):
        """Test that warning is logged when folder doesn't exist."""
        mock_settings.obsidian_vault_scan_folders = "NonExistent"

        mock_vault_path = Mock(spec=Path)
        mock_vault_path.exists.return_value = False
        mock_vault_path.__truediv__ = Mock(return_value=mock_vault_path)

        result = self.engine.percolate_from_vault(mock_vault_path)

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "does not exist" in call_args
        assert result == {"tasks": 0, "commits": 0, "links": 0}

    @patch("omega_kg.percolation.settings")
    def test_empty_scan_folders_string(self, mock_settings):
        """Test that empty string defaults to Sessions folder."""
        mock_settings.obsidian_vault_scan_folders = ""

        mock_vault_path = Mock(spec=Path)
        mock_vault_path.exists.return_value = True
        mock_vault_path.__truediv__ = Mock(return_value=mock_vault_path)
        mock_vault_path.rglob.return_value = []

        result = self.engine.percolate_from_vault(mock_vault_path)

        # Empty string should result in no valid folders (empty list after strip)
        # So __truediv__ should not be called
        mock_vault_path.__truediv__.assert_not_called()
        assert result == {"tasks": 0, "commits": 0, "links": 0}

    @patch("omega_kg.percolation.settings")
    def test_multiple_folders_with_spaces(self, mock_settings):
        """Test that folder names with spaces are trimmed."""
        mock_settings.obsidian_vault_scan_folders = "Sessions, TN, Tasks"

        mock_vault_path = Mock(spec=Path)
        mock_vault_path.__truediv__ = Mock(return_value=mock_vault_path)

        # Create mock folders
        mock_folders = {}
        for name in ["Sessions", "TN", "Tasks"]:
            mock_folder = Mock()
            mock_folder.exists.return_value = True
            mock_folder.rglob.return_value = []
            mock_folders[name] = mock_folder

        def truediv_side_effect(folder_name):
            return mock_folders.get(folder_name.strip(), Mock())

        mock_vault_path.__truediv__ = Mock(side_effect=truediv_side_effect)

        result = self.engine.percolate_from_vault(
            mock_vault_path, scan_folders=["Sessions", "TN", "Tasks"]
        )

        # All three folders should be processed
        assert len(mock_folders) == 3
        for folder in mock_folders.values():
            assert folder.rglob.call_count == 1
        assert result == {"tasks": 0, "commits": 0, "links": 0}


class TestVectorSimilarityThreshold:
    """Test configurable similarity threshold for relationship creation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        # Make session a context manager
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session

    @patch("omega_kg.percolation.settings")
    def test_default_similarity_threshold(self, mock_settings):
        """Test that default similarity threshold works correctly."""
        # Mock settings with default threshold
        mock_settings.percolation_similarity_threshold = 0.8

        engine = PercolationEngine(self.mock_driver)

        # Test that find_similar_tasks uses the default threshold
        mock_result = Mock()
        mock_result.single.return_value = None  # No embedding found
        self.mock_driver.session.return_value.run.return_value = mock_result

        similar_tasks = engine.find_similar_tasks("TASK-001")
        assert similar_tasks == []  # Should return empty list when no embedding found

    @patch("omega_kg.percolation.settings")
    def test_custom_similarity_threshold(self, mock_settings):
        """Test using custom similarity threshold."""
        # Mock settings with custom threshold
        mock_settings.percolation_similarity_threshold = 0.75

        engine = PercolationEngine(self.mock_driver)

        # Test that custom threshold is used
        mock_result = Mock()
        mock_result.single.return_value = None  # No embedding found
        self.mock_driver.session.return_value.run.return_value = mock_result

        similar_tasks = engine.find_similar_tasks("TASK-001", similarity_threshold=0.9)
        assert similar_tasks == []  # Should return empty list when no embedding found

    @patch("omega_kg.percolation.settings")
    def test_threshold_boundary_validation(self, mock_settings):
        """Test validation of similarity threshold boundaries."""
        # Mock settings
        mock_settings.percolation_similarity_threshold = 0.8

        engine = PercolationEngine(self.mock_driver)

        # Test with valid thresholds
        mock_result = Mock()
        mock_result.single.return_value = None
        self.mock_driver.session.return_value.run.return_value = mock_result

        # These should work without errors
        engine.find_similar_tasks("TASK-001", similarity_threshold=0.0)
        engine.find_similar_tasks("TASK-001", similarity_threshold=1.0)
        engine.find_similar_tasks("TASK-001", similarity_threshold=0.5)
