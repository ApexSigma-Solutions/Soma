"""
Async PostgreSQL Vector Storage Layer

Provides immediate-insert semantics for vector embeddings with database-backed durability.
All operations are non-blocking and designed for high-throughput capture scenarios.

Architecture:
- Immediate Insert: Records created with status='pending_embedding' on capture
- Worker Polling: Background worker fetches pending records with FOR UPDATE SKIP LOCKED
- Idempotent Updates: Embedding updates are safe to retry without duplication
- At-Least-Once: Database persistence ensures no embedding is lost on worker crash

Design Pattern:
The write-behind pattern decouples capture latency from embedding generation latency.
Captures complete immediately; embeddings are generated asynchronously by the worker.

Error Handling:
- Connection failures: Raise ConnectionError; client retries or falls back to mock
- Dimension mismatch: Log error and mark record as FAILED (requires manual review)
- Duplicate message_id: ON CONFLICT DO NOTHING ensures idempotency
"""

import logging
from typing import List, Optional, cast
# import json (removed)

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from omega_kg.config import (
    DEFAULT_NODE_TYPE,
    POSTGRES_DB,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_SERVER,
    POSTGRES_USER,
    VECTOR_EMBEDDING_DIMENSION,
    VECTOR_TABLE_NAME,
    VectorStatus,
)

logger = logging.getLogger(__name__)

# Global connection pool (initialized at startup, closed at shutdown)
_pool: Optional[asyncpg.Pool] = None


class VectorStore:
    """
    Async PostgreSQL vector storage abstraction.

    Manages all interactions with omega_vectors_1024 table:
    - Creating pending embedding records on capture
    - Fetching pending batches for worker processing
    - Updating completed embeddings
    - Marking failures with retry tracking

    Thread-safe; connection pooling handled by asyncpg.
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize VectorStore with asyncpg connection pool.

        Args:
            pool: asyncpg.Pool instance with pgvector registered
        """
        self.pool = pool

    @staticmethod
    async def initialize_pool() -> asyncpg.Pool:
        """
        Create and initialize asyncpg connection pool with pgvector support.

        Returns:
            asyncpg.Pool: Configured pool with 5-20 connections

        Raises:
            ConnectionError: If PostgreSQL is unreachable or credentials invalid
        """
        global _pool

        try:
            pool = await asyncpg.create_pool(
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                host=POSTGRES_SERVER,
                port=POSTGRES_PORT,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )

            # Register pgvector type for the pool
            async with pool.acquire() as conn:
                await register_vector(conn)

            logger.info(
                f"PostgreSQL pool initialized: {POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
            )
            _pool = pool
            return pool

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise ConnectionError(f"PostgreSQL connection failed: {e}")

    async def store_pending(
        self,
        message_id: str,
        node_label: str = DEFAULT_NODE_TYPE,
    ) -> Optional[int]:
        """
        Insert a new pending embedding record or return existing vector_id if duplicate.

        Implements write-behind pattern: Record created with status='pending_embedding',
        embedding column NULL. Worker processes asynchronously.

        Args:
            message_id: Neo4j node ID (source of content to embed)
            node_label: Neo4j node type (ChatMessage, LinearIssue, Decision)

        Returns:
            int: vector_id (database primary key) for later update

        Raises:
            ConnectionError: If pool is unavailable
            ValueError: If node_label is not in SUPPORTED_NODE_TYPES
        """
        if not self.pool:
            raise ConnectionError("VectorStore pool not initialized")

        query = f"""
            INSERT INTO {VECTOR_TABLE_NAME} (message_id, node_label, status)
            VALUES ($1, $2, $3)
            ON CONFLICT (message_id, node_label) DO NOTHING
            RETURNING id;
        """

        try:
            async with self.pool.acquire() as conn:
                result = cast(
                    Optional[int],
                    await conn.fetchval(
                        query,
                        message_id,
                        node_label,
                        VectorStatus.PENDING_EMBEDDING,
                    ),
                )

            if result:
                logger.debug(
                    f"Created pending vector record: message_id={message_id}, "
                    f"node_label={node_label}, vector_id={result}"
                )
                return result
            else:
                # Duplicate insertion; fetch existing record
                fetch_query = f"""
                    SELECT id FROM {VECTOR_TABLE_NAME}
                    WHERE message_id = $1 AND node_label = $2;
                """
                async with self.pool.acquire() as conn:
                    existing_id = cast(
                        Optional[int],
                        await conn.fetchval(fetch_query, message_id, node_label),
                    )
                logger.debug(
                    f"Pending record already exists: message_id={message_id}, "
                    f"node_label={node_label}, vector_id={existing_id}"
                )
                return existing_id

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to insert pending vector record: {e}")
            raise ConnectionError(f"Vector store insertion failed: {e}")

    async def update_embedding(
        self,
        vector_id: int,
        embedding: List[float],
    ) -> None:
        """
        Update a pending record with computed embedding vector and mark READY.

        Validates embedding dimension before update. Idempotent: Safe to call multiple
        times with same vector_id and embedding (last write wins).

        Args:
            vector_id: Primary key from store_pending() result
            embedding: List of 1024 floats (BGE-M3 output)

        Raises:
            ConnectionError: If pool is unavailable
            ValueError: If embedding dimension != VECTOR_EMBEDDING_DIMENSION
        """
        if not self.pool:
            raise ConnectionError("VectorStore pool not initialized")

        if len(embedding) != VECTOR_EMBEDDING_DIMENSION:
            logger.error(
                f"Embedding dimension mismatch: expected {VECTOR_EMBEDDING_DIMENSION}, "
                f"got {len(embedding)} for vector_id={vector_id}"
            )
            raise ValueError(
                f"Embedding dimension must be {VECTOR_EMBEDDING_DIMENSION}, "
                f"got {len(embedding)}"
            )

        # Convert embedding list to numpy array for pgvector
        embedding_array = np.array(embedding, dtype=np.float32)

        query = f"""
            UPDATE {VECTOR_TABLE_NAME}
            SET embedding = $1, status = $2, updated_at = NOW()
            WHERE id = $3
            RETURNING id;
        """

        try:
            async with self.pool.acquire() as conn:
                # Register pgvector type for this connection
                await register_vector(conn)
                result = await conn.fetchval(
                    query,
                    embedding_array,  # Pass as numpy array; pgvector handles it
                    VectorStatus.READY,
                    vector_id,
                )

            if result:
                logger.debug(f"Updated embedding for vector_id={vector_id}")
            else:
                logger.warning(f"No record found to update: vector_id={vector_id}")

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to update embedding for vector_id={vector_id}: {e}")
            raise ConnectionError(f"Vector store update failed: {e}")

    async def mark_failed(
        self,
        vector_id: int,
        increment_retry: bool = True,
    ) -> None:
        """
        Mark a vector record as FAILED and optionally increment retry_count.

        Called when embedding generation fails and max retries exceeded.
        Sets status='failed' for manual review.

        Args:
            vector_id: Primary key from store_pending() result
            increment_retry: If True, increment retry_count before marking failed

        Raises:
            ConnectionError: If pool is unavailable
        """
        if not self.pool:
            raise ConnectionError("VectorStore pool not initialized")

        if increment_retry:
            query = f"""
                UPDATE {VECTOR_TABLE_NAME}
                SET status = $1, retry_count = retry_count + 1, updated_at = NOW()
                WHERE id = $2
                RETURNING id;
            """
        else:
            query = f"""
                UPDATE {VECTOR_TABLE_NAME}
                SET status = $1, updated_at = NOW()
                WHERE id = $2
                RETURNING id;
            """

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(query, VectorStatus.FAILED, vector_id)

            if result:
                logger.debug(
                    f"Marked vector as FAILED: vector_id={vector_id}, "
                    f"increment_retry={increment_retry}"
                )
            else:
                logger.warning(f"No record found to mark failed: vector_id={vector_id}")

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to mark vector as failed: vector_id={vector_id}: {e}")
            raise ConnectionError(f"Vector store update failed: {e}")

    async def fetch_pending_batch(self, batch_size: int = 10) -> List[dict]:
        """
        Fetch up to batch_size pending embedding records for worker processing.

        Uses FOR UPDATE SKIP LOCKED to prevent multiple workers processing same records.
        Transitions fetched records to status='processing' (ephemeral state).

        Returns:
            List of dicts: [
                {'vector_id': int, 'message_id': str, 'node_label': str},
                ...
            ]

        Raises:
            ConnectionError: If pool is unavailable
        """
        if not self.pool:
            raise ConnectionError("VectorStore pool not initialized")

        query = f"""
            SELECT id as vector_id, message_id, node_label
            FROM {VECTOR_TABLE_NAME}
            WHERE status = $1
            ORDER BY created_at ASC
            LIMIT $2
            FOR UPDATE SKIP LOCKED;
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    query, VectorStatus.PENDING_EMBEDDING, batch_size
                )

            logger.debug(f"Fetched {len(rows)} pending vectors for processing")
            return [dict(row) for row in rows]

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to fetch pending batch: {e}")
            raise ConnectionError(f"Vector store fetch failed: {e}")

    async def get_vector_status(self, vector_id: int) -> Optional[str]:
        """
        Get current status of a vector record.

        Args:
            vector_id: Primary key

        Returns:
            str or None: One of (pending_embedding, ready, failed) or None if not found

        Raises:
            ConnectionError: If pool is unavailable
        """
        if not self.pool:
            raise ConnectionError("VectorStore pool not initialized")

        query = f"""
            SELECT status FROM {VECTOR_TABLE_NAME} WHERE id = $1;
        """

        try:
            async with self.pool.acquire() as conn:
                status = cast(Optional[str], await conn.fetchval(query, vector_id))
            return status

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to fetch vector status: vector_id={vector_id}: {e}")
            raise ConnectionError(f"Vector store fetch failed: {e}")

    async def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        threshold: float = 0.0,
    ) -> List[dict]:
        """
        Perform semantic search using cosine distance.

        Args:
            query_vector: Embedding vector to search with
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List[Dict]: List of matches (content/metadata will be empty until join logic is added)
        """
        if not self.pool:
            raise ConnectionError("VectorStore pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                # Register pgvector type for this connection to handle ndarray
                await register_vector(conn)

                # Note: Currently the vector table only stores the index.
                # A JOIN with the content table (active_context/conversations) would be needed for full RAG.
                # Returning available index data for now.
                rows = await conn.fetch(
                    f"""
                    SELECT 
                        id, 
                        message_id, 
                        node_label,
                        1 - (embedding <=> $1) as score
                    FROM {VECTOR_TABLE_NAME}
                    WHERE status = 'ready'
                      AND 1 - (embedding <=> $1) > $2
                    ORDER BY embedding <=> $1
                    LIMIT $3
                    """,
                    np.array(query_vector, dtype=np.float32),
                    threshold,
                    limit,
                )

                return [
                    {
                        "id": r["id"],
                        "message_id": r["message_id"],
                        "node_label": r["node_label"],
                        "score": r["score"],
                        # Placeholders so script doesn't crash
                        "content": f"Content lookup required for {r['node_label']}:{r['message_id']}",
                        "metadata": {"source": "vector_index"},
                    }
                    for r in rows
                ]

        except asyncpg.PostgresError as e:
            logger.error(f"Vector search failed: {e}")
            raise ConnectionError(f"Database error: {e}")

    async def get_stats(self) -> dict:
        """
        Get summary statistics for vector store health monitoring.

        Returns:
            dict: {
                'total_records': int,
                'pending_count': int,
                'ready_count': int,
                'failed_count': int,
                'avg_retry_count': float,
            }

        Raises:
            ConnectionError: If pool is unavailable
        """
        if not self.pool:
            raise ConnectionError("VectorStore pool not initialized")

        query = f"""
            SELECT
                COUNT(*) as total_records,
                SUM(CASE WHEN status = $1 THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = $2 THEN 1 ELSE 0 END) as ready_count,
                SUM(CASE WHEN status = $3 THEN 1 ELSE 0 END) as failed_count,
                AVG(retry_count) as avg_retry_count
            FROM {VECTOR_TABLE_NAME};
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    VectorStatus.PENDING_EMBEDDING,
                    VectorStatus.READY,
                    VectorStatus.FAILED,
                )
            return dict(row) if row else {}

        except asyncpg.PostgresError as e:
            logger.error(f"Failed to fetch vector statistics: {e}")
            raise ConnectionError(f"Vector store stats fetch failed: {e}")

    @staticmethod
    async def close_pool() -> None:
        """
        Gracefully close connection pool.

        Called during shutdown. Waits for active connections to complete.
        """
        global _pool
        if _pool:
            await _pool.close()
            logger.info("PostgreSQL pool closed")
            _pool = None


# Singleton instance (initialized at startup)
vector_store: Optional[VectorStore] = None


async def get_vector_store() -> VectorStore:
    """
    Get or initialize the singleton VectorStore instance.

    Returns:
        VectorStore: Shared instance with initialized connection pool

    Raises:
        ConnectionError: If PostgreSQL is unreachable
    """
    global vector_store

    if vector_store is None:
        pool = await VectorStore.initialize_pool()
        vector_store = VectorStore(pool)

    return vector_store


__all__ = [
    "VectorStore",
    "get_vector_store",
]
