"""
PGVectorStore: PostgreSQL-based vector storage with pgvector extension.

This module provides the primary storage layer for memos.MCP, replacing Qdrant
with native PostgreSQL vector operations using the pgvector extension.

Features:
- Async connection pooling via asyncpg
- Vector similarity search using cosine distance
- Full audit logging of all memory operations
- Support for metadata and tag-based filtering
"""

import logging
from typing import Any, Dict, List, Optional

import asyncpg
from asyncpg import Pool

from ..config import settings
from ..services import ollama_service

logger = logging.getLogger(__name__)


class PGVectorStore:
    """
    PostgreSQL vector store implementation using pgvector.

    Uses the 'memos' schema with:
    - memories: Main table storing content, embeddings, and metadata
    - memory_audit: Audit log for all operations
    """

    def __init__(
        self,
        pool: Optional[Pool] = None,
        schema: Optional[str] = None,
        embedding_dimension: Optional[int] = None,
    ):
        """
        Initialize PGVectorStore.

        Args:
            pool: Optional asyncpg connection pool. If not provided, one will
                  be created on first use.
            schema: Database schema name (default: from settings)
            embedding_dimension: Vector dimension (default: from settings)
        """
        self._pool = pool
        self._schema = schema or settings.postgres_schema
        self._embedding_dimension = embedding_dimension or settings.embedding_dimension
        self._initialized = False

    async def _get_pool(self) -> Pool:
        """Get or create the connection pool."""
        if self._pool is None:
            dsn = (
                f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
                f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            )
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
            logger.info("Created asyncpg connection pool")
        return self._pool

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed asyncpg connection pool")

    async def _log_audit(
        self,
        conn: asyncpg.Connection,
        memory_id: Optional[int],
        operation: str,
        agent_id: Optional[str],
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an operation to the audit table."""
        import json

        await conn.execute(
            f"""
            INSERT INTO {self._schema}.memory_audit 
            (memory_id, operation, agent_id, details)
            VALUES ($1, $2, $3, $4)
            """,
            memory_id,
            operation,
            agent_id,
            json.dumps(details) if details else None,
        )

    # =========================================================================
    # STORE OPERATIONS
    # =========================================================================

    async def store_memory(
        self,
        content: str,
        agent_id: str = "default_agent",
        embedding: Optional[List[float]] = None,
        embedding_model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """
        Store a memory with optional embedding.

        Args:
            content: The text content of the memory
            agent_id: ID of the agent storing the memory
            embedding: Optional vector embedding (1024 dimensions)
            embedding_model: Name of the model used to generate embedding
            metadata: Optional JSONB metadata
            tags: Optional list of tags

        Returns:
            The ID of the stored memory
        """
        import json

        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Convert embedding to pgvector format if provided
            embedding_str = None
            if embedding:
                if len(embedding) != self._embedding_dimension:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {self._embedding_dimension}, "
                        f"got {len(embedding)}"
                    )
                embedding_str = f"[{','.join(map(str, embedding))}]"

            memory_id = await conn.fetchval(
                f"""
                INSERT INTO {self._schema}.memories 
                (content, agent_id, embedding, embedding_model, memory_metadata, tags)
                VALUES ($1, $2, $3::vector, $4, $5, $6)
                RETURNING id
                """,
                content,
                agent_id,
                embedding_str,
                embedding_model,
                json.dumps(metadata) if metadata else None,
                tags,
            )

            await self._log_audit(
                conn,
                memory_id,
                "INSERT",
                agent_id,
                {
                    "content_length": len(content),
                    "has_embedding": embedding is not None,
                },
            )

            logger.debug(f"Stored memory {memory_id} for agent {agent_id}")
            return memory_id

    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================

    async def search_memories(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        agent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using vector similarity.

        Args:
            query_embedding: The query vector (1024 dimensions)
            top_k: Maximum number of results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
            agent_id: Optional filter by agent ID
            tags: Optional filter by tags (any match)

        Returns:
            List of matching memories with similarity scores
        """
        if len(query_embedding) != self._embedding_dimension:
            raise ValueError(
                f"Query embedding dimension mismatch: expected {self._embedding_dimension}, "
                f"got {len(query_embedding)}"
            )

        pool = await self._get_pool()
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Build query with optional filters
        where_clauses = ["embedding IS NOT NULL"]
        params: List[Any] = [embedding_str, top_k]
        param_idx = 3

        if agent_id:
            where_clauses.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        if tags:
            where_clauses.append(f"tags && ${param_idx}")
            params.append(tags)
            param_idx += 1

        where_sql = " AND ".join(where_clauses)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT 
                    id,
                    content,
                    agent_id,
                    memory_metadata,
                    tags,
                    created_at,
                    updated_at,
                    1 - (embedding <=> $1::vector) as similarity
                FROM {self._schema}.memories
                WHERE {where_sql}
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                *params,
            )

            results = []
            for row in rows:
                similarity = float(row["similarity"])
                if similarity >= score_threshold:
                    results.append(
                        {
                            "id": row["id"],
                            "content": row["content"],
                            "agent_id": row["agent_id"],
                            "metadata": row["memory_metadata"],
                            "tags": row["tags"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                            "similarity": similarity,
                        }
                    )

            logger.debug(f"Search returned {len(results)} results")
            return results

    # =========================================================================
    # RETRIEVE OPERATIONS
    # =========================================================================

    async def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single memory by ID.

        Args:
            memory_id: The ID of the memory

        Returns:
            The memory dict or None if not found
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT id, content, agent_id, memory_metadata, tags,
                       embedding_model, created_at, updated_at
                FROM {self._schema}.memories
                WHERE id = $1
                """,
                memory_id,
            )

            if row:
                return {
                    "id": row["id"],
                    "content": row["content"],
                    "agent_id": row["agent_id"],
                    "metadata": row["memory_metadata"],
                    "tags": row["tags"],
                    "embedding_model": row["embedding_model"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    async def get_memories_by_agent(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories for a specific agent.

        Args:
            agent_id: The agent ID to filter by
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of memories
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, content, agent_id, memory_metadata, tags,
                       embedding_model, created_at, updated_at
                FROM {self._schema}.memories
                WHERE agent_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                agent_id,
                limit,
                offset,
            )

            return [
                {
                    "id": row["id"],
                    "content": row["content"],
                    "agent_id": row["agent_id"],
                    "metadata": row["memory_metadata"],
                    "tags": row["tags"],
                    "embedding_model": row["embedding_model"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    async def delete_memory(self, memory_id: int, agent_id: str = "system") -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: The ID of the memory to delete
            agent_id: The agent performing the deletion (for audit)

        Returns:
            True if deleted, False if not found
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    f"DELETE FROM {self._schema}.memories WHERE id = $1",
                    memory_id,
                )
                deleted = result == "DELETE 1"

                if deleted:
                    await self._log_audit(conn, memory_id, "DELETE", agent_id, None)
                    logger.debug(f"Deleted memory {memory_id}")

                return deleted

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    async def update_embedding(
        self,
        memory_id: int,
        embedding: List[float],
        embedding_model: str,
        agent_id: str = "system",
    ) -> bool:
        """
        Update the embedding for an existing memory.

        Args:
            memory_id: The ID of the memory
            embedding: The new embedding vector
            embedding_model: Name of the model used
            agent_id: The agent performing the update (for audit)

        Returns:
            True if updated, False if not found
        """
        if len(embedding) != self._embedding_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self._embedding_dimension}, "
                f"got {len(embedding)}"
            )

        pool = await self._get_pool()
        embedding_str = f"[{','.join(map(str, embedding))}]"

        async with pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    f"""
                    UPDATE {self._schema}.memories
                    SET embedding = $1::vector, embedding_model = $2
                    WHERE id = $3
                    """,
                    embedding_str,
                    embedding_model,
                    memory_id,
                )
                updated = result == "UPDATE 1"

                if updated:
                    await self._log_audit(
                        conn,
                        memory_id,
                        "UPDATE_EMBEDDING",
                        agent_id,
                        {"embedding_model": embedding_model},
                    )
                    logger.debug(f"Updated embedding for memory {memory_id}")

                return updated

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            total_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM {self._schema}.memories"
            )
            embedded_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM {self._schema}.memories WHERE embedding IS NOT NULL"
            )
            agent_counts = await conn.fetch(
                f"""
                SELECT agent_id, COUNT(*) as count 
                FROM {self._schema}.memories 
                GROUP BY agent_id
                """
            )

            return {
                "total_memories": total_count,
                "embedded_memories": embedded_count,
                "memories_by_agent": {r["agent_id"]: r["count"] for r in agent_counts},
            }

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a real embedding from text using Ollama.

        Args:
            text: The text to generate an embedding for

        Returns:
            A 1024-dimension embedding (if using bge-m3)
        """
        return await ollama_service.get_embedding(text)


# Global instance (lazy initialization)
_pgvector_store: Optional[PGVectorStore] = None


def get_pgvector_store() -> PGVectorStore:
    """Get the global PGVectorStore instance."""
    global _pgvector_store
    if _pgvector_store is None:
        _pgvector_store = PGVectorStore()
    return _pgvector_store


async def init_pgvector_store() -> PGVectorStore:
    """Initialize and return the global PGVectorStore instance."""
    store = get_pgvector_store()
    await store._get_pool()  # Ensure pool is created
    return store
