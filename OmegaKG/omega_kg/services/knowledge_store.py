"""Knowledge storage service for atomic Neo4j and pgvector writes.

This service handles the atomic storage of validated knowledge digests
to both Neo4j (graph structure) and pgvector (semantic search).
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

from neo4j import AsyncDriver, AsyncSession
import asyncpg

from ..models.validation_schemas import KnowledgeDigest, DigestType
from ..settings import Settings


logger = logging.getLogger(__name__)


class KnowledgeStoreError(Exception):
    """Base exception for knowledge storage errors."""

    pass


class KnowledgeStore:
    """Service for storing validated knowledge in Neo4j and pgvector.

    This service ensures atomic writes to both databases - if either
    write fails, both are rolled back to maintain consistency.
    """

    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        pg_pool: asyncpg.Pool,
        settings: Settings,
    ):
        """Initialize knowledge store.

        Args:
            neo4j_driver: Neo4j async driver
            pg_pool: PostgreSQL connection pool
            settings: Application settings
        """
        self.neo4j_driver = neo4j_driver
        self.pg_pool = pg_pool
        self.settings = settings

    async def store_knowledge(
        self,
        digest: KnowledgeDigest,
    ) -> Tuple[str, int]:
        """Store knowledge digest in Neo4j and pgvector atomically.

        This method performs atomic writes to both databases:
        1. Create Neo4j node with knowledge metadata
        2. Create pgvector record with embedding
        3. Rollback both if either fails

        Args:
            digest: Validated knowledge digest

        Returns:
            Tuple[str, int]: (neo4j_node_id, vector_id)

        Raises:
            KnowledgeStoreError: If storage fails
        """
        neo4j_session: Optional[AsyncSession] = None
        pg_conn: Optional[asyncpg.Connection] = None
        neo4j_node_id: Optional[str] = None
        vector_id: Optional[int] = None

        try:
            # Start Neo4j session
            neo4j_session = self.neo4j_driver.session()

            # Start PostgreSQL transaction
            pg_conn = await self.pg_pool.acquire()
            pg_tx = pg_conn.transaction()
            await pg_tx.start()

            # STEP 1: Create Neo4j node
            neo4j_node_id = await self._create_neo4j_node(neo4j_session, digest)
            logger.info(f"Created Neo4j node: {neo4j_node_id} for {digest.source_id}")

            # STEP 2: Create pgvector record
            vector_id = await self._create_vector_record(pg_conn, digest, neo4j_node_id)
            logger.info(f"Created vector record: {vector_id} for {digest.source_id}")

            # STEP 3: Commit both transactions
            await pg_tx.commit()

            logger.info(
                f"Successfully stored knowledge: {digest.source_id} "
                f"(neo4j={neo4j_node_id}, vector={vector_id})"
            )

            return (neo4j_node_id, vector_id)

        except Exception as e:
            # Rollback on any error
            logger.error(f"Failed to store knowledge {digest.source_id}: {e}")

            # Rollback PostgreSQL transaction
            if pg_conn and pg_tx:
                try:
                    await pg_tx.rollback()
                    logger.info("Rolled back PostgreSQL transaction")
                except Exception as rollback_error:
                    logger.error(f"PostgreSQL rollback failed: {rollback_error}")

            # Delete Neo4j node if created
            if neo4j_node_id and neo4j_session:
                try:
                    await self._delete_neo4j_node(neo4j_session, neo4j_node_id)
                    logger.info(f"Rolled back Neo4j node: {neo4j_node_id}")
                except Exception as rollback_error:
                    logger.error(f"Neo4j rollback failed: {rollback_error}")

            raise KnowledgeStoreError(f"Failed to store knowledge: {e}") from e

        finally:
            # Clean up resources
            if pg_conn:
                await self.pg_pool.release(pg_conn)
            if neo4j_session:
                await neo4j_session.close()

    async def _create_neo4j_node(
        self,
        session: AsyncSession,
        digest: KnowledgeDigest,
    ) -> str:
        """Create Neo4j node based on digest type.

        Args:
            session: Neo4j session
            digest: Knowledge digest

        Returns:
            str: Neo4j node ID
        """
        # Determine node label based on digest type
        label_mapping = {
            DigestType.CONVERSATION: "ChatSession",
            DigestType.TERMINAL_EVENT: "TerminalExecution",
            DigestType.LINEAR_ISSUE: "LinearIssue",
            DigestType.GITHUB_PR: "GitHubPR",
        }
        label = label_mapping.get(digest.digest_type, "KnowledgeNode")

        # Create node with common properties
        query = f"""
        CREATE (n:{label} {{
            source_id: $source_id,
            title: $title,
            content: $content,
            summary: $summary,
            tags: $tags,
            captured_at: datetime($captured_at),
            processed_at: datetime($processed_at),
            created_at: datetime($created_at),
            metadata: $metadata
        }})
        RETURN elementId(n) as node_id
        """

        result = await session.run(
            query,
            source_id=str(digest.source_id),
            title=digest.title,
            content=digest.content,
            summary=digest.summary,
            tags=digest.tags,
            captured_at=digest.captured_at.isoformat(),
            processed_at=digest.processed_at.isoformat(),
            created_at=datetime.utcnow().isoformat(),
            metadata=digest.metadata,
        )

        record = await result.single()
        node_id = record["node_id"]

        # --- Handle Relationships (References) ---
        if digest.references:
            # 1. DevSession relationship (CONTAINS)
            session_ids = digest.references.get("session_id", [])
            for session_id in session_ids:
                if session_id:
                    rel_query = """
                    MATCH (n) WHERE elementId(n) = $node_id
                    MERGE (s:DevSession {id: $session_id})
                    MERGE (s)-[:CONTAINS]->(n)
                    """
                    await session.run(rel_query, node_id=node_id, session_id=session_id)

            # 2. LinearIssue relationship (RESOLVES_OR_RELATES)
            issue_ids = digest.references.get("linear_issue", [])
            for issue_id in issue_ids:
                if issue_id:
                    rel_query = """
                    MATCH (n) WHERE elementId(n) = $node_id
                    MATCH (i:LinearIssue {identifier: $issue_id})
                    MERGE (n)-[:RESOLVES_OR_RELATES]->(i)
                    """
                    await session.run(rel_query, node_id=node_id, issue_id=issue_id)

        return node_id

    async def _create_vector_record(
        self,
        conn: asyncpg.Connection,
        digest: KnowledgeDigest,
        neo4j_node_id: str,
    ) -> int:
        """Create pgvector record with embedding.

        Args:
            conn: PostgreSQL connection
            digest: Knowledge digest
            neo4j_node_id: Associated Neo4j node ID

        Returns:
            int: Vector record ID
        """
        query = """
        INSERT INTO omega_vectors_1024 (
            message_id,
            neo4j_node_id,
            content,
            embedding,
            status,
            created_at,
            metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """

        vector_id = await conn.fetchval(
            query,
            digest.source_id,
            neo4j_node_id,
            digest.content,
            digest.embedding,  # pgvector handles list -> vector conversion
            "READY",
            datetime.utcnow(),
            digest.metadata,
        )

        return vector_id

    async def _delete_neo4j_node(
        self,
        session: AsyncSession,
        node_id: str,
    ) -> None:
        """Delete Neo4j node by element ID (rollback operation).

        Args:
            session: Neo4j session
            node_id: Neo4j element ID
        """
        query = """
        MATCH (n)
        WHERE elementId(n) = $node_id
        DELETE n
        """

        await session.run(query, node_id=node_id)

    async def check_duplicate(
        self,
        source_id: str,
        digest_type: DigestType,
    ) -> bool:
        """Check if knowledge with source_id already exists.

        Args:
            source_id: Source identifier
            digest_type: Digest type

        Returns:
            bool: True if duplicate exists
        """
        label_mapping = {
            DigestType.CONVERSATION: "ChatSession",
            DigestType.TERMINAL_EVENT: "TerminalExecution",
            DigestType.LINEAR_ISSUE: "LinearIssue",
            DigestType.GITHUB_PR: "GitHubPR",
        }
        label = label_mapping.get(digest_type, "KnowledgeNode")

        async with self.neo4j_driver.session() as session:
            query = f"""
            MATCH (n:{label} {{source_id: $source_id}})
            RETURN count(n) as count
            """

            result = await session.run(query, source_id=source_id)
            record = await result.single()
            return record["count"] > 0
