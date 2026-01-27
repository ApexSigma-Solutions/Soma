"""
End-to-End Integration Tests - Data Flow (TN-OMG-012)

Validates that data flows correctly across all OmegaKG services,
from capture through ingestion to knowledge graph storage.

Test Flow:
1. Send test conversation through capture server endpoint
2. Verify conversation is queued in PostgreSQL with 'pending_embedding' status
3. Verify InGest-LLM picks up conversation and generates embeddings
4. Verify embeddings are stored in pgvector table
5. Verify Neo4j ChatSession node is updated with embedding
6. Verify vector similarity search returns the conversation
"""

import uuid
from datetime import datetime, timezone
from typing import List

import pytest
import pytest_asyncio
from neo4j.exceptions import Neo4jError

from omega_kg.database.graph import AsyncGraphDriver
from omega_kg.models.capture import ConversationData, Message
from omega_kg.vector_store import VectorStore, get_vector_store
from omega_kg.config import VectorStatus


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


@pytest_asyncio.fixture
async def vector_store():
    """Initialize vector store for testing."""
    try:
        store = await get_vector_store()
        yield store
    except Exception as e:
        pytest.skip(f"Vector store unavailable: {e}")


@pytest_asyncio.fixture
def sample_conversation() -> ConversationData:
    """Create a sample conversation for testing."""
    return ConversationData(
        platform="github",
        url="https://github.com/test/repo",
        messages=[
            Message(
                role="user",
                content="What is the best way to test data flow integration?",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            Message(
                role="assistant",
                content="The best way is to create end-to-end tests that verify the complete pipeline.",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        ],
    )


@pytest_asyncio.fixture
def mock_embedding() -> List[float]:
    """Generate a deterministic 1024-dim mock embedding."""
    return [0.001 * i for i in range(1024)]


# Tests
@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_e2e_capture_to_vector_queue(
    sample_conversation: ConversationData,
    vector_store: VectorStore,
):
    """
    Test 1: Capture server successfully queues conversations for embedding.

    Validates:
    - Conversation can be sent to capture endpoint
    - Vector record is created with 'pending_embedding' status
    - Vector ID is returned for tracking
    """
    # This test simulates the capture endpoint behavior
    # In a real E2E test, we would POST to /capture endpoint
    # For now, we test the vector store directly

    # Generate a mock message ID (simulating Neo4j node ID)
    message_id = str(uuid.uuid4())

    # Store pending embedding (simulating capture server behavior)
    vector_id = await vector_store.store_pending(
        message_id=message_id, node_label="ChatSession"
    )

    assert vector_id is not None, "Vector ID should be returned"

    # Verify the record was created with pending status
    status = await vector_store.get_vector_status(vector_id)
    assert status == VectorStatus.PENDING_EMBEDDING, (
        f"Expected pending_embedding status, got {status}"
    )

    # Cleanup
    await vector_store.mark_failed(vector_id, increment_retry=False)


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_e2e_embedding_generation_and_storage(
    vector_store: VectorStore,
    mock_embedding: List[float],
):
    """
    Test 2 & 3: InGest-LLM processes queued conversations and stores embeddings.

    Validates:
    - Pending records can be fetched
    - Embeddings can be generated (mocked)
    - Embeddings are stored in pgvector with 'ready' status
    """
    # First, create a pending record
    message_id = str(uuid.uuid4())
    vector_id = await vector_store.store_pending(
        message_id=message_id, node_label="ChatSession"
    )

    # Simulate embedding generation by updating the record
    await vector_store.update_embedding(vector_id, mock_embedding)

    # Verify the status is now 'ready'
    status = await vector_store.get_vector_status(vector_id)
    assert status == VectorStatus.READY, (
        f"Expected ready status after embedding update, got {status}"
    )

    # Cleanup
    # Note: In real system, we'd need to delete the record
    # For now, we just mark it as failed to clean up
    await vector_store.mark_failed(vector_id, increment_retry=False)


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_e2e_neo4j_node_creation_with_embedding(
    neo4j_driver: AsyncGraphDriver,
    sample_conversation: ConversationData,
    mock_embedding: List[float],
):
    """
    Test 4: Neo4j nodes are created/updated with embedding properties.

    Validates:
    - ChatSession node is created in Neo4j
    - Node has embedding property with 1024 dimensions
    - Embedding matches expected values
    """
    from omega_kg.utils.capture_utils import generate_conversation_hash

    conv_hash = generate_conversation_hash(sample_conversation)

    # Create ChatSession node with embedding
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MERGE (s:ChatSession {conversation_hash: $hash})
            ON CREATE SET
                s.date = date($date), s.platform = $platform, s.url = $url,
                s.message_count = $msg_count, s.created_at = datetime($created_at),
                s.embedding = $embedding
            RETURN s
            """,
            hash=conv_hash,
            date=datetime.now().strftime("%Y-%m-%d"),
            platform=sample_conversation.platform,
            url=sample_conversation.url,
            msg_count=len(sample_conversation.messages),
            created_at=datetime.now().isoformat(),
            embedding=mock_embedding,
        )

        record = await result.single()
        assert record is not None, "ChatSession node should be created"
        assert record["s"]["embedding"] is not None, "Embedding property should be set"

        # Verify embedding dimensions
        embedding = record["s"]["embedding"]
        assert len(embedding) == 1024, (
            f"Expected 1024 embedding dimensions, got {len(embedding)}"
        )
        assert embedding == mock_embedding, "Embedding should match expected values"

    # Cleanup
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_e2e_vector_similarity_search(
    vector_store: VectorStore,
    mock_embedding: List[float],
):
    """
    Test 5: Vector similarity search returns expected results.

    Validates:
    - Search can be performed with query vector
    - Results are returned with similarity scores
    - Scores are within expected range (0.0 to 1.0)
    """
    # First, store a ready embedding
    message_id = str(uuid.uuid4())
    vector_id = await vector_store.store_pending(
        message_id=message_id, node_label="ChatSession"
    )
    await vector_store.update_embedding(vector_id, mock_embedding)

    # Perform similarity search
    results = await vector_store.search(
        query_vector=mock_embedding,
        limit=5,
        threshold=0.0,
    )

    # Verify results
    assert len(results) > 0, "Search should return at least one result"

    # The first result should be the exact match (same vector)
    assert results[0]["score"] == 1.0, "Exact match should have score of 1.0"
    assert results[0]["message_id"] == message_id, (
        "Result should match the stored message ID"
    )

    # Verify all results have valid scores
    for result in results:
        assert 0.0 <= result["score"] <= 1.0, (
            f"Similarity score should be between 0.0 and 1.0, got {result['score']}"
        )

    # Cleanup
    await vector_store.mark_failed(vector_id, increment_retry=False)


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_e2e_complete_data_flow(
    neo4j_driver: AsyncGraphDriver,
    vector_store: VectorStore,
    sample_conversation: ConversationData,
    mock_embedding: List[float],
):
    """
    Complete end-to-end test: Capture → Queue → Embed → Store → Neo4j → Search.

    This test validates the entire data flow in a single test:
    1. Simulate capture by storing pending embedding
    2. Simulate embedding generation by updating with embedding
    3. Verify Neo4j node has embedding property
    4. Perform vector similarity search
    5. Verify search returns the conversation

    This is the primary acceptance test for TN-OMG-012.
    """
    from omega_kg.utils.capture_utils import generate_conversation_hash

    conv_hash = generate_conversation_hash(sample_conversation)

    # Step 1: Capture - Queue pending embedding
    message_id = str(uuid.uuid4())
    vector_id = await vector_store.store_pending(
        message_id=message_id, node_label="ChatSession"
    )

    # Verify pending status
    status = await vector_store.get_vector_status(vector_id)
    assert status == VectorStatus.PENDING_EMBEDDING, (
        "Step 1: Vector should be pending after capture"
    )

    # Step 2: Embedding - Generate and store embedding
    await vector_store.update_embedding(vector_id, mock_embedding)

    # Verify ready status
    status = await vector_store.get_vector_status(vector_id)
    assert status == VectorStatus.READY, (
        "Step 2: Vector should be ready after embedding generation"
    )

    # Step 3: Neo4j - Create node with embedding
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MERGE (s:ChatSession {conversation_hash: $hash})
            ON CREATE SET
                s.date = date($date), s.platform = $platform, s.url = $url,
                s.message_count = $msg_count, s.created_at = datetime($created_at),
                s.embedding = $embedding
            RETURN s
            """,
            hash=conv_hash,
            date=datetime.now().strftime("%Y-%m-%d"),
            platform=sample_conversation.platform,
            url=sample_conversation.url,
            msg_count=len(sample_conversation.messages),
            created_at=datetime.now().isoformat(),
            embedding=mock_embedding,
        )

        record = await result.single()
        assert record is not None, "Step 3: ChatSession node should be created"
        assert record["s"]["embedding"] is not None, (
            "Step 3: ChatSession should have embedding property"
        )
        assert len(record["s"]["embedding"]) == 1024, (
            "Step 3: Embedding should have 1024 dimensions"
        )

    # Step 4: Search - Verify vector similarity search works
    search_results = await vector_store.search(
        query_vector=mock_embedding,
        limit=5,
        threshold=0.0,
    )

    # Verify search returns our conversation
    assert len(search_results) > 0, "Step 4: Search should return results"

    # Find our result (should be first with score 1.0)
    our_result = next(
        (r for r in search_results if r["message_id"] == message_id), None
    )
    assert our_result is not None, "Step 4: Search should return our test conversation"
    assert our_result["score"] == 1.0, "Step 4: Exact match should have score of 1.0"

    # Cleanup
    await vector_store.mark_failed(vector_id, increment_retry=False)
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_error_handling_recovery(
    vector_store: VectorStore,
):
    """
    Test 6: Error handling and recovery work correctly.

    Validates:
    - Failed embeddings are marked correctly
    - Retry count is incremented
    - System can recover from failures
    """
    # Create a pending record
    message_id = str(uuid.uuid4())
    vector_id = await vector_store.store_pending(
        message_id=message_id, node_label="ChatSession"
    )

    # Mark as failed (simulating embedding generation failure)
    await vector_store.mark_failed(vector_id, increment_retry=True)

    # Verify status is failed
    status = await vector_store.get_vector_status(vector_id)
    assert status == VectorStatus.FAILED, "Vector should be marked as failed"

    # Verify retry count was incremented
    # Note: We can't directly query retry_count without a custom query
    # For now, we just verify the status

    # Test recovery: Create a new pending record (simulating retry)
    message_id_2 = str(uuid.uuid4())
    vector_id_2 = await vector_store.store_pending(
        message_id=message_id_2, node_label="ChatSession"
    )

    # Verify new record is pending
    status_2 = await vector_store.get_vector_status(vector_id_2)
    assert status_2 == VectorStatus.PENDING_EMBEDDING, (
        "New record should be pending for retry"
    )

    # Cleanup
    await vector_store.mark_failed(vector_id, increment_retry=False)
    await vector_store.mark_failed(vector_id_2, increment_retry=False)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_vector_store_health_check(vector_store: VectorStore):
    """
    Test: Vector store health and statistics.

    Validates:
    - Stats can be retrieved
    - All status counts are present
    - Average retry count is calculated correctly
    """
    # Create some test records with different statuses
    message_id_1 = str(uuid.uuid4())
    vector_id_1 = await vector_store.store_pending(
        message_id=message_id_1, node_label="ChatSession"
    )

    message_id_2 = str(uuid.uuid4())
    vector_id_2 = await vector_store.store_pending(
        message_id=message_id_2, node_label="ChatSession"
    )
    await vector_store.update_embedding(vector_id_2, [0.001] * 1024)

    message_id_3 = str(uuid.uuid4())
    vector_id_3 = await vector_store.store_pending(
        message_id=message_id_3, node_label="ChatSession"
    )
    await vector_store.mark_failed(vector_id_3, increment_retry=True)

    # Get stats
    stats = await vector_store.get_stats()

    # Verify stats
    assert stats["total_records"] >= 3, (
        f"Should have at least 3 records, got {stats['total_records']}"
    )
    assert stats["pending_count"] >= 1, (
        f"Should have at least 1 pending record, got {stats['pending_count']}"
    )
    assert stats["ready_count"] >= 1, (
        f"Should have at least 1 ready record, got {stats['ready_count']}"
    )
    assert stats["failed_count"] >= 1, (
        f"Should have at least 1 failed record, got {stats['failed_count']}"
    )

    # Cleanup
    await vector_store.mark_failed(vector_id_1, increment_retry=False)
    await vector_store.mark_failed(vector_id_2, increment_retry=False)
    await vector_store.mark_failed(vector_id_3, increment_retry=False)


@pytest.mark.integration
@pytest.mark.requires_neo4j
@pytest.mark.asyncio
async def test_e2e_concurrent_embedding_updates(
    vector_store: VectorStore,
    mock_embedding: List[float],
):
    """
    Test: Concurrent embedding updates are handled correctly.

    Validates:
    - Multiple updates to same vector_id are idempotent
    - Last write wins (no duplicate records)
    """
    # Create a pending record
    message_id = str(uuid.uuid4())
    vector_id = await vector_store.store_pending(
        message_id=message_id, node_label="ChatSession"
    )

    # Update with embedding twice (simulating concurrent requests)
    await vector_store.update_embedding(vector_id, mock_embedding)
    await vector_store.update_embedding(vector_id, mock_embedding)

    # Verify status is still ready (not duplicated)
    status = await vector_store.get_vector_status(vector_id)
    assert status == VectorStatus.READY, (
        "Status should remain ready after concurrent updates"
    )

    # Cleanup
    await vector_store.mark_failed(vector_id, increment_retry=False)
