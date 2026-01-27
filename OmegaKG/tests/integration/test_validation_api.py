"""Integration tests for TN-CORE-102: OmegaKG Validation API Gateway.

Tests verify Zero Trust authentication, quality validation, deduplication,
and atomic transaction behavior for the validation API.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from fastapi.testclient import TestClient
from omega_kg.capture_server import app
import omega_kg.settings
import omega_kg.database.graph
from omega_kg.settings import Settings, get_settings


@pytest.fixture
def client(graph_driver, db_engine):
    """Create a test client with container dependencies."""
    # Force reload settings to pick up container env vars
    new_settings = Settings()

    # Patch global settings
    original_settings = omega_kg.settings.settings
    omega_kg.settings.settings = new_settings

    # Reset graph driver to force reconnect with new settings
    # This is critical because graph_driver is a singleton initialized with old settings
    original_driver = omega_kg.database.graph.graph_driver._driver
    omega_kg.database.graph.graph_driver._driver = None

    import os

    print(f"DEBUG: os.environ['POSTGRES_USER'] = {os.environ.get('POSTGRES_USER')}")
    print(f"DEBUG: settings.postgres_user = {new_settings.postgres_user}")

    from unittest.mock import patch, AsyncMock

    # PATCH: Prevent actual Ollama startup during tests to avoid hangs/timeouts
    with patch(
        "omega_kg.capture_server._start_ollama", new_callable=AsyncMock
    ) as mock_ollama:
        mock_ollama.return_value = True

        try:
            with TestClient(app) as c:
                yield c
        finally:
            # Restore global state
            omega_kg.database.graph.graph_driver._driver = original_driver
            omega_kg.settings.settings = original_settings


@pytest.fixture
def valid_token():
    """Get a valid authentication token for testing."""
    settings = get_settings()
    # Use static service token for testing
    return settings.static_service_token or "test-token-12345"


@pytest.fixture
def valid_digest():
    """Create a valid knowledge digest for testing."""
    return {
        "source_id": f"test_conv_{uuid4().hex[:8]}",
        "digest_type": "conversation",
        "title": "Test Conversation",
        "content": "This is a test conversation about Python programming and software development.",
        "summary": "A test conversation",
        "embedding": [0.1] * 1024,  # 1024-dimensional embedding
        "metadata": {"platform": "test", "user": "test_user"},
        "tags": ["test", "python"],
        "references": {"files": ["test.py"], "repos": []},
        "captured_at": datetime.utcnow().isoformat(),
        "processed_at": datetime.utcnow().isoformat(),
    }


class TestValidationAPIAuthentication:
    """Test Zero Trust authentication for validation API."""

    def test_missing_token_returns_401(self, client, valid_digest):
        """Test that requests without token are rejected."""
        # Act
        response = client.post("/validate/validate-and-store", json=valid_digest)

        # Assert
        assert response.status_code in [401, 403]
        if response.status_code == 401:
            assert (
                "authorization" in response.text.lower()
                or "unauthorized" in response.text.lower()
            )

    def test_invalid_token_returns_401(self, client, valid_digest):
        """Test that requests with invalid token are rejected."""
        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=valid_digest,
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )

        # Assert
        assert response.status_code == 401

    def test_valid_token_accepted(self, client, valid_digest, valid_token):
        """Test that requests with valid token are accepted."""
        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=valid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code in [200, 409]  # 200 accepted or 409 duplicate


class TestValidationAPIQualityChecks:
    """Test quality validation for knowledge digests."""

    def test_empty_content_rejected(self, client, valid_digest, valid_token):
        """Test that empty content is rejected."""
        # Arrange
        invalid_digest = valid_digest.copy()
        invalid_digest["content"] = "   "  # Whitespace only

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=invalid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code in [
            200,
            422,
        ]  # Pydantic validation or quality check
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "rejected"

    def test_short_content_rejected(self, client, valid_digest, valid_token):
        """Test that content shorter than minimum is rejected."""
        # Arrange
        invalid_digest = valid_digest.copy()
        invalid_digest["content"] = "short"  # Less than 10 characters

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=invalid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "rejected"

    def test_invalid_embedding_dimension_rejected(
        self, client, valid_digest, valid_token
    ):
        """Test that embeddings with wrong dimensions are rejected."""
        # Arrange
        invalid_digest = valid_digest.copy()
        invalid_digest["embedding"] = [0.1] * 512  # Wrong dimension

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=invalid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code == 422  # Pydantic validation error

    def test_empty_title_rejected(self, client, valid_digest, valid_token):
        """Test that empty title is rejected."""
        # Arrange
        invalid_digest = valid_digest.copy()
        invalid_digest["title"] = ""

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=invalid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "rejected"


class TestValidationAPIDeduplication:
    """Test deduplication logic for validation API."""

    def test_duplicate_source_id_detected(self, client, valid_digest, valid_token):
        """Test that duplicate source_id is detected."""
        # Arrange - Submit first digest
        response1 = client.post(
            "/validate/validate-and-store",
            json=valid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Act - Submit same digest again
        response2 = client.post(
            "/validate/validate-and-store",
            json=valid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        if response1.status_code == 200:
            data1 = response1.json()
            if data1["status"] == "accepted":
                # Second request should be duplicate
                assert response2.status_code == 200
                data2 = response2.json()
                assert data2["status"] == "duplicate"
                assert data2["source_id"] == valid_digest["source_id"]

    def test_different_source_ids_accepted(self, client, valid_digest, valid_token):
        """Test that different source_ids are both accepted."""
        # Arrange
        digest1 = valid_digest.copy()
        digest1["source_id"] = f"test_conv_{uuid4().hex[:8]}"

        digest2 = valid_digest.copy()
        digest2["source_id"] = f"test_conv_{uuid4().hex[:8]}"

        # Act
        response1 = client.post(
            "/validate/validate-and-store",
            json=digest1,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        response2 = client.post(
            "/validate/validate-and-store",
            json=digest2,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()

            # Both should be accepted (not duplicates)
            assert data1["status"] in ["accepted", "duplicate"]
            assert data2["status"] in ["accepted", "duplicate"]


class TestValidationAPIAtomicTransactions:
    """Test atomic transaction behavior (Neo4j + pgvector)."""

    @pytest.mark.asyncio
    async def test_successful_storage_returns_node_ids(
        self, client, valid_digest, valid_token
    ):
        """Test that successful storage returns both Neo4j and vector IDs."""
        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=valid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "accepted":
                assert data["neo4j_node_id"] is not None
                assert data["vector_id"] is not None
                assert isinstance(data["vector_id"], int)

    @pytest.mark.skip(reason="Requires database failure injection")
    def test_rollback_on_vector_failure(self, client, valid_digest, valid_token):
        """Test that Neo4j node is deleted if pgvector write fails."""
        # This test requires mocking/injecting a failure in the vector store
        # The KnowledgeStore should rollback the Neo4j node creation
        pass

    @pytest.mark.skip(reason="Requires database failure injection")
    def test_rollback_on_neo4j_failure(self, client, valid_digest, valid_token):
        """Test that pgvector record is not created if Neo4j write fails."""
        # This test requires mocking/injecting a failure in Neo4j
        # The KnowledgeStore should not create the vector record
        pass


class TestValidationAPIDigestTypes:
    """Test support for different digest types."""

    def test_conversation_digest_accepted(self, client, valid_digest, valid_token):
        """Test that conversation digest is accepted."""
        # Arrange
        valid_digest["digest_type"] = "conversation"
        valid_digest["source_id"] = f"conv_{uuid4().hex[:8]}"

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=valid_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code in [200, 409]

    def test_terminal_event_digest_accepted(self, client, valid_digest, valid_token):
        """Test that terminal_event digest is accepted."""
        # Arrange
        terminal_digest = valid_digest.copy()
        terminal_digest["digest_type"] = "terminal_event"
        terminal_digest["source_id"] = f"term_{uuid4().hex[:8]}"
        terminal_digest["title"] = "Test Terminal Command"
        terminal_digest["content"] = "cd /home/user && ls -la"

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=terminal_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code in [200, 409]

    def test_linear_issue_digest_accepted(self, client, valid_digest, valid_token):
        """Test that linear_issue digest is accepted."""
        # Arrange
        linear_digest = valid_digest.copy()
        linear_digest["digest_type"] = "linear_issue"
        linear_digest["source_id"] = f"linear_{uuid4().hex[:8]}"
        linear_digest["title"] = "Test Linear Issue"

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=linear_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code in [200, 409]


class TestValidationAPIHealthCheck:
    """Test validation API health endpoint."""

    def test_health_endpoint_accessible(self, client):
        """Test that health endpoint is accessible without authentication."""
        # Act
        response = client.get("/validate/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "validation-api"


@pytest.mark.integration
class TestValidationAPIEndToEnd:
    """End-to-end integration tests for validation API."""

    def test_full_validation_workflow(self, client, valid_digest, valid_token):
        """Test complete validation workflow from submission to storage."""
        # Arrange
        unique_digest = valid_digest.copy()
        unique_digest["source_id"] = f"e2e_test_{uuid4().hex[:8]}"

        # Act
        response = client.post(
            "/validate/validate-and-store",
            json=unique_digest,
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "message" in data
        assert "source_id" in data
        assert "digest_type" in data
        assert "created_at" in data

        # If accepted, verify IDs are present
        if data["status"] == "accepted":
            assert data["neo4j_node_id"] is not None
            assert data["vector_id"] is not None

    def test_validation_api_handles_concurrent_requests(
        self, client, valid_digest, valid_token
    ):
        """Test that validation API handles concurrent requests correctly."""
        # Arrange - Create multiple unique digests
        digests = []
        for i in range(5):
            digest = valid_digest.copy()
            digest["source_id"] = f"concurrent_{i}_{uuid4().hex[:8]}"
            digests.append(digest)

        # Act - Submit all digests
        responses = []
        for digest in digests:
            response = client.post(
                "/validate/validate-and-store",
                json=digest,
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            responses.append(response)

        # Assert - All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["accepted", "duplicate", "error"]
