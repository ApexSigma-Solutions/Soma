"""
Unit tests for omega_kg.settings module
"""

from omega_kg.settings import Settings


def test_settings_load_from_env(monkeypatch):
    """Test that settings load correctly from environment variables"""
    # Set explicit environment variables
    monkeypatch.setenv("NEO4J_URI", "bolt://test-host:7687")
    monkeypatch.setenv("NEO4J_USER", "test-user")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("APP_ENV", "production")

    settings = Settings()

    assert settings.neo4j_uri == "bolt://test-host:7687"
    assert settings.neo4j_user == "test-user"
    assert settings.neo4j_password == "test-password"
    assert settings.app_env == "production"


def test_settings_defaults():
    """Test that Settings has correct default values defined.

    This verifies the model schema defaults, not runtime values which
    can be overridden by environment variables.
    """
    from pydantic_core import PydanticUndefined

    from omega_kg.settings import Settings

    # Check model defaults via model_fields
    fields = Settings.model_fields

    assert fields["app_env"].default == "development"
    assert fields["neo4j_uri"].default == "bolt://localhost:7687"
    assert fields["neo4j_user"].default == "neo4j"
    # neo4j_password has no default (PydanticUndefined = required)
    assert fields["neo4j_password"].default is PydanticUndefined


def test_settings_singleton():
    """Test that settings is a singleton instance"""
    from omega_kg.settings import settings as settings1
    from omega_kg.settings import settings as settings2

    assert settings1 is settings2


def test_settings_creates_valid_driver_config():
    """Test that settings provide valid Neo4j driver configuration"""
    settings = Settings()

    # Verify settings has required Neo4j connection parameters
    assert settings.neo4j_uri
    assert settings.neo4j_user
    assert settings.neo4j_password
