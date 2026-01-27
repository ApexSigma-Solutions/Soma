"""
Unit tests for PGVectorStore.

Tests cover:
- Connection pool management
- Memory storage with embeddings
- Semantic search operations
- CRUD operations (get, update, delete)
- Audit logging
- Statistics
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import unittest
from datetime import datetime, timezone

import sys

sys.path.insert(0, "src")


class TestPGVectorStoreUnit:
    """Unit tests for PGVectorStore using mocks."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock asyncpg connection pool."""
        pool = MagicMock()
        conn = MagicMock()

        # Create async methods on connection
        conn.fetchval = AsyncMock()
        conn.fetch = AsyncMock()
        conn.fetchrow = AsyncMock()
        conn.execute = AsyncMock()

        # Create transaction context manager
        tx_cm = MagicMock()
        tx_cm.__aenter__ = AsyncMock(return_value=None)
        tx_cm.__aexit__ = AsyncMock(return_value=None)
        conn.transaction.return_value = tx_cm

        # Create pool.acquire() async context manager
        pool_cm = MagicMock()
        pool_cm.__aenter__ = AsyncMock(return_value=conn)
        pool_cm.__aexit__ = AsyncMock(return_value=None)
        pool.acquire.return_value = pool_cm

        # Make pool.close() async
        pool.close = AsyncMock()

        return pool, conn

    @pytest.fixture
    def store(self):
        """Create a PGVectorStore instance."""
        from memos_mcp.database.pgvector_store import PGVectorStore

        return PGVectorStore(schema="memos", embedding_dimension=1024)

    # =========================================================================
    # EMBEDDING GENERATION TESTS
    # =========================================================================

    # =========================================================================
    # EMBEDDING GENERATION TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, store):
        """Test successful embedding generation."""
        with unittest.mock.patch(
            "memos_mcp.database.pgvector_store.ollama_service"
        ) as mock_service:
            mock_service.get_embedding = AsyncMock(return_value=[0.1] * 1024)

            embedding = await store.generate_embedding("test")

            assert len(embedding) == 1024
            assert embedding[0] == 0.1
            mock_service.get_embedding.assert_called_once_with("test")

    # =========================================================================
    # STORE MEMORY TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_store_memory_success(self, store, mock_pool):
        """Test successful memory storage."""
        pool, conn = mock_pool
        store._pool = pool
        conn.fetchval.return_value = 42
        conn.execute.return_value = None

        embedding = [0.1] * 1024
        memory_id = await store.store_memory(
            content="test content",
            agent_id="test_agent",
            embedding=embedding,
            embedding_model="test_model",
            metadata={"key": "value"},
            tags=["tag1", "tag2"],
        )

        assert memory_id == 42
        conn.fetchval.assert_called_once()
        # Verify audit was logged
        assert conn.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_store_memory_without_embedding(self, store, mock_pool):
        """Test storing memory without embedding."""
        pool, conn = mock_pool
        store._pool = pool
        conn.fetchval.return_value = 1
        conn.execute.return_value = None

        memory_id = await store.store_memory(
            content="test content",
            agent_id="test_agent",
        )

        assert memory_id == 1

    @pytest.mark.asyncio
    async def test_store_memory_wrong_embedding_dimension(self, store, mock_pool):
        """Test that wrong embedding dimension raises error."""
        pool, conn = mock_pool
        store._pool = pool

        embedding = [0.1] * 512  # Wrong dimension

        with pytest.raises(ValueError, match="dimension mismatch"):
            await store.store_memory(
                content="test",
                embedding=embedding,
            )

    # =========================================================================
    # SEARCH TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_search_memories_success(self, store, mock_pool):
        """Test successful semantic search."""
        pool, conn = mock_pool
        store._pool = pool

        # Mock search results
        mock_row = {
            "id": 1,
            "content": "test content",
            "agent_id": "test_agent",
            "memory_metadata": {"key": "value"},
            "tags": ["tag1"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "similarity": 0.85,
        }
        conn.fetch.return_value = [mock_row]

        query_embedding = [0.1] * 1024
        results = await store.search_memories(
            query_embedding=query_embedding,
            top_k=5,
        )

        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["similarity"] == 0.85

    @pytest.mark.asyncio
    async def test_search_memories_with_threshold(self, store, mock_pool):
        """Test search with score threshold."""
        pool, conn = mock_pool
        store._pool = pool

        # Return result below threshold
        mock_row = {
            "id": 1,
            "content": "test",
            "agent_id": "agent",
            "memory_metadata": None,
            "tags": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "similarity": 0.3,  # Below threshold
        }
        conn.fetch.return_value = [mock_row]

        results = await store.search_memories(
            query_embedding=[0.1] * 1024,
            score_threshold=0.5,  # Threshold
        )

        assert len(results) == 0  # Filtered out

    @pytest.mark.asyncio
    async def test_search_memories_wrong_dimension(self, store, mock_pool):
        """Test search with wrong query dimension."""
        pool, conn = mock_pool
        store._pool = pool

        with pytest.raises(ValueError, match="dimension mismatch"):
            await store.search_memories(
                query_embedding=[0.1] * 512,
            )

    @pytest.mark.asyncio
    async def test_search_memories_with_agent_filter(self, store, mock_pool):
        """Test search filtered by agent ID."""
        pool, conn = mock_pool
        store._pool = pool
        conn.fetch.return_value = []

        await store.search_memories(
            query_embedding=[0.1] * 1024,
            agent_id="specific_agent",
        )

        # Verify the query includes agent filter
        call_args = conn.fetch.call_args
        assert "specific_agent" in call_args[0]

    # =========================================================================
    # RETRIEVE TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_memory_found(self, store, mock_pool):
        """Test retrieving existing memory."""
        pool, conn = mock_pool
        store._pool = pool

        mock_row = {
            "id": 1,
            "content": "test content",
            "agent_id": "test_agent",
            "memory_metadata": {"key": "value"},
            "tags": ["tag1"],
            "embedding_model": "test_model",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        conn.fetchrow.return_value = mock_row

        result = await store.get_memory(1)

        assert result is not None
        assert result["id"] == 1
        assert result["content"] == "test content"

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, store, mock_pool):
        """Test retrieving non-existent memory."""
        pool, conn = mock_pool
        store._pool = pool
        conn.fetchrow.return_value = None

        result = await store.get_memory(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_memories_by_agent(self, store, mock_pool):
        """Test retrieving memories by agent."""
        pool, conn = mock_pool
        store._pool = pool

        mock_rows = [
            {
                "id": 1,
                "content": "memory 1",
                "agent_id": "agent1",
                "memory_metadata": None,
                "tags": None,
                "embedding_model": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": 2,
                "content": "memory 2",
                "agent_id": "agent1",
                "memory_metadata": None,
                "tags": None,
                "embedding_model": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]
        conn.fetch.return_value = mock_rows

        results = await store.get_memories_by_agent("agent1", limit=10)

        assert len(results) == 2

    # =========================================================================
    # DELETE TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, store, mock_pool):
        """Test successful memory deletion."""
        pool, conn = mock_pool
        store._pool = pool
        conn.execute.return_value = "DELETE 1"

        result = await store.delete_memory(1, "test_agent")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, store, mock_pool):
        """Test deleting non-existent memory."""
        pool, conn = mock_pool
        store._pool = pool
        conn.execute.return_value = "DELETE 0"

        result = await store.delete_memory(999, "test_agent")

        assert result is False

    # =========================================================================
    # UPDATE TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_embedding_success(self, store, mock_pool):
        """Test successful embedding update."""
        pool, conn = mock_pool
        store._pool = pool
        conn.execute.return_value = "UPDATE 1"

        result = await store.update_embedding(
            memory_id=1,
            embedding=[0.2] * 1024,
            embedding_model="new_model",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_embedding_wrong_dimension(self, store, mock_pool):
        """Test update with wrong embedding dimension."""
        pool, conn = mock_pool
        store._pool = pool

        with pytest.raises(ValueError, match="dimension mismatch"):
            await store.update_embedding(
                memory_id=1,
                embedding=[0.1] * 512,
                embedding_model="model",
            )

    # =========================================================================
    # STATS TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_stats(self, store, mock_pool):
        """Test getting memory statistics."""
        pool, conn = mock_pool
        store._pool = pool

        conn.fetchval.side_effect = [100, 80]  # total, embedded
        conn.fetch.return_value = [
            {"agent_id": "agent1", "count": 50},
            {"agent_id": "agent2", "count": 50},
        ]

        stats = await store.get_stats()

        assert stats["total_memories"] == 100
        assert stats["embedded_memories"] == 80
        assert stats["memories_by_agent"]["agent1"] == 50

    # =========================================================================
    # CONNECTION POOL TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_close_pool(self, store, mock_pool):
        """Test closing the connection pool."""
        pool, _ = mock_pool
        store._pool = pool

        await store.close()

        pool.close.assert_called_once()
        assert store._pool is None

    @pytest.mark.asyncio
    async def test_close_pool_when_none(self, store):
        """Test closing when pool is None."""
        store._pool = None

        # Should not raise
        await store.close()


class TestPGVectorStoreIntegration:
    """
    Integration tests requiring a real PostgreSQL connection.

    These tests are skipped by default. Run with:
        POSTGRES_PASSWORD=omega_dev_password pytest tests/test_pgvector_store.py -v -m integration
    """

    @pytest.fixture
    async def live_store(self):
        """Create a real PGVectorStore connected to the test database."""
        import os

        if not os.environ.get("POSTGRES_PASSWORD"):
            pytest.skip("POSTGRES_PASSWORD not set")

        from memos_mcp.database.pgvector_store import PGVectorStore

        store = PGVectorStore(schema="memos", embedding_dimension=1024)
        await store._get_pool()
        yield store
        await store.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, live_store):
        """Test complete memory lifecycle: store, search, retrieve, delete."""
        store = live_store

        # Store
        content = f"Integration test memory {datetime.now().isoformat()}"
        embedding = store.generate_placeholder_embedding(content)

        memory_id = await store.store_memory(
            content=content,
            agent_id="integration_test",
            embedding=embedding,
            embedding_model="placeholder",
            tags=["integration", "test"],
        )
        assert memory_id > 0

        # Retrieve
        memory = await store.get_memory(memory_id)
        assert memory is not None
        assert memory["content"] == content

        # Search
        query_embedding = store.generate_placeholder_embedding(content)
        results = await store.search_memories(
            query_embedding=query_embedding,
            top_k=5,
        )
        assert any(r["id"] == memory_id for r in results)

        # Delete
        deleted = await store.delete_memory(memory_id, "integration_test_cleanup")
        assert deleted is True

        # Verify deletion
        memory = await store.get_memory(memory_id)
        assert memory is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
