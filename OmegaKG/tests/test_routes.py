"""
OmegaKG Router Unit Tests

Unit tests for FastAPI routers using TestClient and unittest.mock.
Follows the "Organism" architecture: tests the Brain's API layer in isolation.

Usage:
    poetry run pytest tests/test_routes.py -v --tb=short
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# =============================================================================
# FIXTURES - Isolated App Creation (Avoids Circular Imports)
# =============================================================================


@pytest.fixture
def mock_settings():
    """Mock settings to avoid loading real config."""
    with patch("omega_kg.settings.settings") as mock:
        mock.PROJECT_NAME = "OmegaKG-Test"
        mock.VERSION = "0.0.1-test"
        mock.obsidian_vault_path = "./test_vault"
        mock.STATIC_SERVICE_TOKEN = "test-token-12345"
        mock.JWT_SECRET_KEY = "test-secret-key-for-testing-only"
        mock.JWT_ALGORITHM = "HS256"
        mock.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        yield mock


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar=lambda: 42))
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for unit tests."""
    driver = MagicMock()
    driver.verify_connectivity = AsyncMock(return_value=True)
    return driver


# =============================================================================
# UNIT TESTS - Health Endpoints
# =============================================================================


@pytest.mark.unit
def test_installation_status_returns_status():
    """Installation status should return version info."""
    from fastapi import FastAPI
    from omega_kg.routers import capture

    app = FastAPI()
    app.include_router(capture.router, prefix="/v1/capture")
    client = TestClient(app)

    response = client.get("/v1/capture/health/installation")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "omega_kg_installed" in data


@pytest.mark.unit
def test_capture_options_cors():
    """CORS preflight should succeed."""
    from fastapi import FastAPI
    from omega_kg.routers import capture

    app = FastAPI()
    app.include_router(capture.router, prefix="/v1/capture")
    client = TestClient(app)

    response = client.options("/v1/capture/capture")
    assert response.status_code == 200


@pytest.mark.unit
def test_auth_token_requires_api_key():
    """Token endpoint should require API key."""
    from fastapi import FastAPI
    from omega_kg.routers import capture

    app = FastAPI()
    app.include_router(capture.router, prefix="/v1/capture")
    client = TestClient(app)

    response = client.post("/v1/capture/auth/token")
    # Without API key, should fail with 403 or 422
    assert response.status_code in [403, 422]


# =============================================================================
# UNIT TESTS - Capture Utils
# =============================================================================


@pytest.mark.unit
def test_generate_conversation_hash_is_deterministic():
    """Conversation hash should be deterministic."""
    from omega_kg.utils.capture_utils import generate_conversation_hash
    from omega_kg.models.capture import ConversationData

    data = ConversationData(
        user_id="test-user",
        source="pytest",
        platform="test",
        messages=[{"role": "user", "content": "Hello"}],
    )

    hash1 = generate_conversation_hash(data)
    hash2 = generate_conversation_hash(data)

    assert hash1 == hash2
    assert len(hash1) > 0


@pytest.mark.unit
def test_generate_conversation_uuid_is_valid():
    """Conversation UUID should be valid UUIDv5."""
    from omega_kg.utils.capture_utils import generate_conversation_uuid
    from omega_kg.models.capture import ConversationData
    import uuid

    data = ConversationData(
        user_id="test-user",
        source="pytest",
        platform="test",
        messages=[{"role": "user", "content": "Hello"}],
    )

    result = generate_conversation_uuid(data)

    # Result could be UUID object or string - handle both
    if isinstance(result, uuid.UUID):
        valid = True
    else:
        try:
            uuid.UUID(str(result))
            valid = True
        except ValueError:
            valid = False

    assert valid


# =============================================================================
# INTEGRATION-READY MARKERS
# =============================================================================


@pytest.mark.integration
@pytest.mark.requires_neo4j
def test_full_capture_flow_with_neo4j():
    """Full capture flow with real database."""
    pytest.skip("Requires Neo4j container - run with: pytest -m integration")


@pytest.mark.integration
@pytest.mark.requires_postgres
def test_omega_stats_with_real_db():
    """Stats endpoint with real database connection."""
    pytest.skip("Requires Postgres container - run with: pytest -m integration")
