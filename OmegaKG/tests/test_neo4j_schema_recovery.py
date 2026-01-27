"""
Unit tests for omega_kg.neo4j_schema module
"""

from unittest.mock import MagicMock, patch
from omega_kg.neo4j_schema import KnowledgeGraphSchema


class TestKnowledgeGraphSchema:
    """Test the KnowledgeGraphSchema class"""

    def test_schema_initialization_mock_mode(self):
        """Test schema initialization in mock mode"""
        schema = KnowledgeGraphSchema(mock_mode=True)

        assert schema.mock_mode is True
        assert schema.driver is None

    def test_schema_initialize_mock_mode(self):
        """Test initialize_schema in mock mode skips operations"""
        schema = KnowledgeGraphSchema(mock_mode=True)

        # Should complete without error
        schema.initialize_schema()

    def test_schema_connection_status_mock(self):
        """Test connection status in mock mode"""
        schema = KnowledgeGraphSchema(mock_mode=True)

        status = schema.get_connection_status()

        assert status["connected"] is False
        assert status["mock_mode"] is True
        assert status["uri"] == "mock://local"

    def test_schema_close_mock_mode(self):
        """
        Verify that calling close() on a KnowledgeGraphSchema created in mock mode completes without raising an error.
        """
        schema = KnowledgeGraphSchema(mock_mode=True)

        # Should complete without error
        schema.close()

    @patch("omega_kg.neo4j_schema.GraphDatabase.driver")
    def test_schema_initialization_with_driver(
        self, mock_driver_class, mock_neo4j_driver
    ):
        """Test schema initialization with mocked driver"""
        mock_driver_class.return_value = mock_neo4j_driver

        with patch("omega_kg.neo4j_schema.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"

            # Mocked session needs to return a result
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.single.return_value = {"status": 1}
            mock_session.run.return_value = mock_result
            mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session

            schema = KnowledgeGraphSchema(mock_mode=False)

            assert schema.driver is not None
            assert schema.mock_mode is False

    @patch("omega_kg.neo4j_schema.GraphDatabase.driver")
    def test_schema_connection_status_with_driver(
        self, mock_driver_class, mock_neo4j_driver
    ):
        """Test connection status with active driver"""
        mock_driver_class.return_value = mock_neo4j_driver

        with patch("omega_kg.neo4j_schema.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"

            # Mock successful health check
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.single.return_value = {"status": 1}
            mock_session.run.return_value = mock_result
            mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session

            schema = KnowledgeGraphSchema(mock_mode=False)
            status = schema.get_connection_status()

            assert status["connected"] is True
            assert status["mock_mode"] is False
