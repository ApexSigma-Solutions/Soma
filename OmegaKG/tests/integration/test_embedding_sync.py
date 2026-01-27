"""
Integration Tests - Embedding Sync (TN-LINEAR-07)

Validates that LinearIssue nodes are correctly enriched with 1024-dim embeddings.
Uses mocked HTTP calls to avoid spending API credits during tests.
"""

import uuid
from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from neo4j.exceptions import Neo4jError
from pydantic import SecretStr

from omega_kg.database.graph import AsyncGraphDriver
from omega_kg.domain.linear.graph_writer import GraphWriter
from omega_kg.domain.linear.models import LinearIssue, LinearState, LinearUser


# Fixtures
@pytest_asyncio.fixture
async def neo4j_driver():
    """Create a fresh Neo4j driver for each test. Skip if unavailable."""
    driver = AsyncGraphDriver()
    try:
        await driver.connect()
    except (Neo4jError, OSError, TimeoutError) as e:
        pytest.skip(f"Neo4j unavailable: {e}")
    yield driver
    await driver.close()


@pytest.fixture
def mock_embedding() -> List[float]:
    """Generate a deterministic 1024-dim mock embedding."""
    return [0.001 * i for i in range(1024)]


@pytest.fixture
def sample_issue() -> LinearIssue:
    """Create a sample LinearIssue for testing."""
    user_id = str(uuid.uuid4())
    issue_id = str(uuid.uuid4())

    assignee = LinearUser(
        id=user_id,
        name="Test User",
        email="test@example.com",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        active=True,
    )

    state = LinearState(
        id=str(uuid.uuid4()),
        name="In Progress",
        color="#F00",
        type="started",
    )

    return LinearIssue(
        id=issue_id,
        identifier="EMB-001",
        title="Test Embedding Issue",
        description="A short description for testing embedding generation.",
        priority=1,
        state=state,
        assignee=assignee,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        url="http://linear.app/issue/EMB-001",
    )


# Tests
@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_upsert_issue_with_embedding(neo4j_driver, sample_issue, mock_embedding):
    """
    Test that an issue with an embedding is correctly stored in Neo4j.

    Validates:
    - Issue node is created
    - Embedding property is stored as a 1024-element list
    """
    writer = GraphWriter(neo4j_driver)

    # Upsert with embedding
    await writer.upsert_issue(sample_issue, embedding=mock_embedding)

    # Verify in Neo4j
    query = """
    MATCH (i:LinearIssue {identifier: $identifier})
    RETURN i.title AS title, i.embedding AS embedding, size(i.embedding) AS dims
    """

    async with neo4j_driver.session() as session:
        result = await session.run(query, {"identifier": sample_issue.identifier})
        record = await result.single()

        assert record is not None, "Issue node not found in graph"
        assert record["title"] == sample_issue.title
        assert record["embedding"] is not None, "Embedding property is missing"
        assert record["dims"] == 1024, f"Expected 1024 dims, got {record['dims']}"

    # Cleanup
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_upsert_issue_without_embedding(neo4j_driver, sample_issue):
    """
    Test that an issue without an embedding is stored correctly.

    The embedding should be None/missing, not an empty list.
    """
    writer = GraphWriter(neo4j_driver)

    # Upsert without embedding
    await writer.upsert_issue(sample_issue, embedding=None)

    # Verify in Neo4j
    query = """
    MATCH (i:LinearIssue {identifier: $identifier})
    RETURN i.title AS title, i.embedding AS embedding
    """

    async with neo4j_driver.session() as session:
        result = await session.run(query, {"identifier": sample_issue.identifier})
        record = await result.single()

        assert record is not None, "Issue node not found in graph"
        assert record["title"] == sample_issue.title
        assert record["embedding"] is None, "Embedding should be None when not provided"

    # Cleanup
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_embedding_dimension_validation(neo4j_driver, sample_issue):
    """
    Test that invalid embedding dimensions raise ValueError.
    """
    writer = GraphWriter(neo4j_driver)

    # Try with wrong dimension count (512 instead of 1024)
    invalid_embedding = [0.0] * 512

    with pytest.raises(ValueError, match="1024"):
        await writer.upsert_issue(sample_issue, embedding=invalid_embedding)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_embedding_nanogpt_success(mock_embedding):
    """
    Test successful embedding generation via Nano-GPT.
    Uses mocked HTTP response to avoid API calls.
    """
    # Create a mock response that behaves like httpx.Response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": mock_embedding}],
        "model": "BAAI/bge-m3",
    }

    # Patch settings at the module level BEFORE function is invoked
    with patch("omega_kg.domain.common.embedding_service.settings") as mock_settings:
        mock_settings.nanogpt_api_key = SecretStr("test-api-key")
        mock_settings.gemini_api_key = None

        with patch(
            "omega_kg.domain.common.embedding_service.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Import the function (settings already patched)
            from omega_kg.domain.common.embedding_service import _embed_nanogpt

            # Generate embedding
            result = await _embed_nanogpt("Test issue title and description")

            # Verify result
            assert len(result) == 1024
            assert result == mock_embedding


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_embedding_fallback_to_gemini():
    """
    Test that embedding generation falls back to Gemini when Nano-GPT fails.
    """
    # Use consistent mock embedding for testing
    mock_embedding = [0.1] * 1024  # Consistent 1024-dim mock embedding

    # Create a mock response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": mock_embedding}],
        "model": "gemini-embedding-001",
    }

    async def mock_post(*_args, **_kwargs):
        return mock_response

    with patch("omega_kg.domain.common.embedding_service.settings") as mock_settings:
        mock_settings.nanogpt_api_key = None
        mock_settings.gemini_api_key = "test-gemini-key"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = mock_post
            mock_client_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            # Import fresh after patching
            import importlib

            from omega_kg.domain.common import embedding_service as emb_module

            importlib.reload(emb_module)

            # Generate embedding using public interface
            result = await emb_module.generate_embedding(
                "Test issue for Gemini fallback"
            )

            # Verify result is correct length
            assert len(result) == 1024
            assert all(isinstance(x, float) for x in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_embedding_no_provider_available():
    """
    Test that appropriate error is raised when no provider is configured.
    """
    # Patch settings at the correct module location where it's imported
    with patch("omega_kg.domain.common.embedding_service.settings") as mock_settings:
        # Configure mock to disable all providers
        mock_settings.ollama_enabled = False
        mock_settings.nano_gpt_enabled = False
        mock_settings.gemini_enabled = False
        mock_settings.nanogpt_api_key = None
        mock_settings.gemini_api_key = None
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.embedding_provider = "mock"

        # Also patch the mock fallback to fail, simulating complete unavailability
        with patch(
            "omega_kg.domain.common.embedding_service._embed_mock",
            side_effect=RuntimeError("Mock embedding also unavailable"),
        ):
            from omega_kg.domain.common.embedding_service import generate_embedding

            with pytest.raises(RuntimeError, match="No embedding provider available"):
                await generate_embedding("Test without any provider")
                await generate_embedding("Test without any provider")
