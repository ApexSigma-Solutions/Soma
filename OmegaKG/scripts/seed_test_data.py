#!/usr/bin/env python3
"""
Test Data Seeding Script for OmegaKG

This script seeds test data into PostgreSQL, Neo4j, and pgvector databases
to verify infrastructure is working correctly and ready for integration testing.

Acceptance Criteria:
- Sample ChatSession nodes created in Neo4j
- Sample conversation records inserted into PostgreSQL
- Vector embeddings stored in pgvector table
- Test data is retrievable and queryable
- Relationships between nodes are properly established

Usage:
    poetry run python scripts/seed_test_data.py
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import asyncpg
from neo4j import AsyncDriver
import numpy as np

from omega_kg.settings import Settings
from omega_kg.config import (
    VECTOR_EMBEDDING_DIMENSION,
    VECTOR_TABLE_NAME,
    VectorStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class TestDataSeeder:
    """Seeds test data into OmegaKG databases."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.neo4j_driver: Optional[AsyncDriver] = None
        self.pg_conn: Optional[asyncpg.Connection] = None

    async def initialize_connections(self) -> None:
        """Initialize database connections."""
        logger.info("Initializing database connections...")

        # Initialize Neo4j connection
        try:
            self.neo4j_driver = AsyncDriver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
                encrypted=False,
            )
            logger.info("Neo4j connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j: {e}")
            raise

        # Initialize PostgreSQL connection
        try:
            self.pg_conn = await asyncpg.connect(
                host=self.settings.postgres_server,
                port=self.settings.postgres_port,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password,
                database=self.settings.postgres_db,
            )
            logger.info("PostgreSQL connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise

    async def close_connections(self) -> None:
        """Close all database connections."""
        if self.neo4j_driver:
            await self.neo4j_driver.close()
            logger.info("Neo4j connection closed")

        if self.pg_conn:
            await self.pg_conn.close()
            logger.info("PostgreSQL connection closed")

    async def seed_neo4j_chat_sessions(self) -> int:
        """Create sample ChatSession nodes in Neo4j."""
        logger.info("Seeding Neo4j ChatSession nodes...")

        chat_sessions = [
            {
                "session_id": "test-session-001",
                "platform": "github",
                "title": "Test GitHub Conversation",
                "created_at": datetime.now() - timedelta(days=7),
                "message_count": 15,
                "metadata": {"test": True, "source": "seeding_script"},
            },
            {
                "session_id": "test-session-002",
                "platform": "claude",
                "title": "Test Claude Conversation",
                "created_at": datetime.now() - timedelta(days=5),
                "message_count": 23,
                "metadata": {"test": True, "source": "seeding_script"},
            },
            {
                "session_id": "test-session-003",
                "platform": "obsidian",
                "title": "Test Obsidian Conversation",
                "created_at": datetime.now() - timedelta(days=3),
                "message_count": 8,
                "metadata": {"test": True, "source": "seeding_script"},
            },
        ]

        nodes_created = 0
        async with self.neo4j_driver.session() as session:
            for session_data in chat_sessions:
                query = """
                CREATE (c:ChatSession {
                    session_id: $session_id,
                    platform: $platform,
                    title: $title,
                    created_at: datetime($created_at),
                    message_count: $message_count,
                    metadata: $metadata
                })
                """

                result = await session.run(
                    query,
                    session_id=session_data["session_id"],
                    platform=session_data["platform"],
                    title=session_data["title"],
                    created_at=session_data["created_at"],
                    message_count=session_data["message_count"],
                    metadata=session_data["metadata"],
                )

                if result:
                    nodes_created += 1
                    logger.info(f"Created ChatSession: {session_data['session_id']}")
                else:
                    logger.error(
                        f"Failed to create ChatSession: {session_data['session_id']}"
                    )

        logger.info(f"Created {nodes_created} ChatSession nodes in Neo4j")
        return nodes_created

    async def seed_postgresql_conversations(self) -> int:
        """Create sample conversation records in PostgreSQL."""
        logger.info("Seeding PostgreSQL conversation records...")

        # First, create the conversations table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id VARCHAR(255) PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            platform VARCHAR(50) NOT NULL,
            user_message TEXT NOT NULL,
            assistant_message TEXT NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """

        async with self.pg_conn.cursor() as cursor:
            await cursor.execute(create_table_query)
            logger.info("Ensured conversations table exists")

        conversations = [
            {
                "conversation_id": "test-conv-001",
                "session_id": "test-session-001",
                "platform": "github",
                "user_message": "Hello, this is a test message from GitHub",
                "assistant_message": "Hi! I'm helping you with your OmegaKG project.",
                "timestamp": datetime.now() - timedelta(hours=2),
                "metadata": {"test": True, "source": "seeding_script"},
            },
            {
                "conversation_id": "test-conv-002",
                "session_id": "test-session-002",
                "platform": "claude",
                "user_message": "Can you help me understand vector embeddings?",
                "assistant_message": "Of course! Vector embeddings are numerical representations of text that capture semantic meaning.",
                "timestamp": datetime.now() - timedelta(hours=1),
                "metadata": {"test": True, "source": "seeding_script"},
            },
            {
                "conversation_id": "test-conv-003",
                "session_id": "test-session-003",
                "platform": "obsidian",
                "user_message": "I need to organize my research notes into knowledge graph.",
                "assistant_message": "Great! The percolation engine can help you link related concepts automatically.",
                "timestamp": datetime.now() - timedelta(minutes=30),
                "metadata": {"test": True, "source": "seeding_script"},
            },
        ]

        records_created = 0
        async with self.pg_conn.cursor() as cursor:
            for conv in conversations:
                query = """
                INSERT INTO conversations (
                    conversation_id, session_id, platform, user_message, assistant_message, 
                    timestamp, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """

                await cursor.execute(
                    query,
                    conv["conversation_id"],
                    conv["session_id"],
                    conv["platform"],
                    conv["user_message"],
                    conv["assistant_message"],
                    conv["timestamp"],
                    json.dumps(conv["metadata"]),
                )
                records_created += 1
                logger.info(f"Created conversation: {conv['conversation_id']}")

        await self.pg_conn.commit()
        logger.info(f"Created {records_created} conversation records in PostgreSQL")
        return records_created

    async def seed_pgvector_embeddings(self) -> int:
        """Create sample vector embeddings in pgvector."""
        logger.info("Seeding pgvector embeddings...")

        # First, ensure pgvector extension is loaded
        await self._ensure_pgvector_extension()

        # Sample embeddings for test conversations
        embeddings = [
            {
                "embedding_id": "test-embed-001",
                "conversation_id": "test-conv-001",
                "embedding": [0.1] * VECTOR_EMBEDDING_DIMENSION,
                "model": "test-model",
                "created_at": datetime.now() - timedelta(hours=2),
                "metadata": {"test": True, "source": "seeding_script"},
            },
            {
                "embedding_id": "test-embed-002",
                "conversation_id": "test-conv-002",
                "embedding": [0.2] * VECTOR_EMBEDDING_DIMENSION,
                "model": "test-model",
                "created_at": datetime.now() - timedelta(hours=1),
                "metadata": {"test": True, "source": "seeding_script"},
            },
            {
                "embedding_id": "test-embed-003",
                "conversation_id": "test-conv-003",
                "embedding": [0.3] * VECTOR_EMBEDDING_DIMENSION,
                "model": "test-model",
                "created_at": datetime.now() - timedelta(minutes=30),
                "metadata": {"test": True, "source": "seeding_script"},
            },
        ]

        embeddings_created = 0
        async with self.pg_conn.cursor() as cursor:
            for embed in embeddings:
                # Convert embedding list to numpy array for pgvector
                embedding_array = np.array(embed["embedding"], dtype=np.float32)

                query = f"""
                INSERT INTO {VECTOR_TABLE_NAME} (id, message_id, embedding, status, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """

                await cursor.execute(
                    query,
                    embed["embedding_id"],
                    embed["conversation_id"],
                    embedding_array,
                    VectorStatus.PENDING_EMBEDDING,
                    embed["created_at"],
                    json.dumps(embed["metadata"]),
                )
                embeddings_created += 1
                logger.info(f"Created embedding: {embed['embedding_id']}")

        await self.pg_conn.commit()
        logger.info(f"Created {embeddings_created} vector embeddings in pgvector")
        return embeddings_created

    async def _ensure_pgvector_extension(self) -> None:
        """Ensure pgvector extension is loaded in PostgreSQL."""
        logger.info("Ensuring pgvector extension is loaded...")

        async with self.pg_conn.cursor() as cursor:
            # Load pgvector extension
            await cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create the omega_vectors_1024 table if it doesn't exist
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {VECTOR_TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                message_id VARCHAR(255) NOT NULL,
                embedding vector({VECTOR_EMBEDDING_DIMENSION}) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending_embedding',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb
            );
            """

            await cursor.execute(create_table_query)
            logger.info(
                f"Ensured {VECTOR_TABLE_NAME} table exists with pgvector extension"
            )

    async def create_relationships(self) -> int:
        """Create relationships between ChatSessions and conversations."""
        logger.info("Creating relationships between nodes...")

        # Create a session_conversations table to track relationships
        create_table_query = """
        CREATE TABLE IF NOT EXISTS session_conversations (
            id SERIAL PRIMARY KEY,
            from_session_id VARCHAR(255) NOT NULL,
            to_conversation_id VARCHAR(255) NOT NULL,
            relationship_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """

        relationships = [
            {
                "from_session_id": "test-session-001",
                "to_conversation_id": "test-conv-001",
                "relationship_type": "CONTAINS",
            },
            {
                "from_session_id": "test-session-002",
                "to_conversation_id": "test-conv-002",
                "relationship_type": "CONTAINS",
            },
            {
                "from_session_id": "test-session-003",
                "to_conversation_id": "test-conv-003",
                "relationship_type": "CONTAINS",
            },
        ]

        relationships_created = 0
        async with self.pg_conn.cursor() as cursor:
            # Ensure table exists
            await cursor.execute(create_table_query)

            for rel in relationships:
                query = """
                INSERT INTO session_conversations (
                    from_session_id, to_conversation_id, relationship_type
                ) VALUES ($1, $2, $3)
                """

                await cursor.execute(
                    query,
                    rel["from_session_id"],
                    rel["to_conversation_id"],
                    rel["relationship_type"],
                )
                relationships_created += 1
                logger.info(
                    f"Created relationship: {rel['from_session_id']} -> {rel['to_conversation_id']}"
                )

        await self.pg_conn.commit()
        logger.info(f"Created {relationships_created} relationships in PostgreSQL")
        return relationships_created

    async def verify_data(self) -> Dict[str, Any]:
        """Verify that test data was seeded correctly."""
        logger.info("Verifying seeded data...")

        verification_results = {}

        # Verify Neo4j ChatSessions
        async with self.neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (c:ChatSession) WHERE c.session_id STARTS WITH 'test-session-' RETURN c.session_id, c.title, COUNT(c) AS session_count"
            )

            if result:
                sessions = [record["c"] for record in result]
                verification_results["neo4j_sessions"] = {
                    "expected": 3,
                    "found": len(sessions),
                    "sessions": [s["session_id"] for s in sessions],
                }
                logger.info(f"Neo4j verification: Found {len(sessions)}/3 ChatSessions")
            else:
                verification_results["neo4j_sessions"] = {
                    "expected": 3,
                    "found": 0,
                    "sessions": [],
                }
                logger.error("Neo4j verification: No ChatSessions found")

        # Verify PostgreSQL conversations
        async with self.pg_conn.cursor() as cursor:
            result = await cursor.execute(
                "SELECT COUNT(*) FROM conversations WHERE metadata->>'test' = 'true'"
            )

            if result:
                count = result[0]["count"]
                verification_results["postgresql_conversations"] = {
                    "expected": 3,
                    "found": count,
                    "status": "✓" if count >= 3 else "✗",
                }
                logger.info(f"PostgreSQL verification: Found {count}/3 conversations")
            else:
                verification_results["postgresql_conversations"] = {
                    "expected": 3,
                    "found": 0,
                    "status": "✗",
                }
                logger.error("PostgreSQL verification: No conversations found")

        # Verify pgvector embeddings
        async with self.pg_conn.cursor() as cursor:
            result = await cursor.execute(
                f"SELECT COUNT(*) FROM {VECTOR_TABLE_NAME} WHERE metadata->>'test' = 'true'"
            )

            if result:
                count = result[0]["count"]
                verification_results["pgvector_embeddings"] = {
                    "expected": 3,
                    "found": count,
                    "status": "✓" if count >= 3 else "✗",
                }
                logger.info(f"pgvector verification: Found {count}/3 embeddings")
            else:
                verification_results["pgvector_embeddings"] = {
                    "expected": 3,
                    "found": 0,
                    "status": "✗",
                }
                logger.error("pgvector verification: No embeddings found")

        # Verify relationships
        async with self.pg_conn.cursor() as cursor:
            result = await cursor.execute(
                "SELECT COUNT(*) FROM session_conversations WHERE from_session_id STARTS WITH 'test-session-'"
            )

            if result:
                count = result[0]["count"]
                verification_results["relationships"] = {
                    "expected": 3,
                    "found": count,
                    "status": "✓" if count >= 3 else "✗",
                }
                logger.info(
                    f"Relationships verification: Found {count}/3 relationships"
                )
            else:
                verification_results["relationships"] = {
                    "expected": 3,
                    "found": 0,
                    "status": "✗",
                }
                logger.error("Relationships verification: No relationships found")

        return verification_results

    async def run(self) -> None:
        """Execute complete seeding process."""
        logger.info("=" * 60)
        logger.info("Starting test data seeding...")

        try:
            # Initialize connections
            await self.initialize_connections()

            # Seed data
            neo4j_count = await self.seed_neo4j_chat_sessions()
            postgres_count = await self.seed_postgresql_conversations()
            pgvector_count = await self.seed_pgvector_embeddings()
            relationships_count = await self.create_relationships()

            # Verify data
            verification_results = await self.verify_data()

            # Print summary
            logger.info("=" * 60)
            logger.info("SEEDING SUMMARY")
            logger.info("=" * 60)
            logger.info(
                f"Neo4j ChatSessions: {verification_results['neo4j_sessions']['found']}/{verification_results['neo4j_sessions']['expected']}"
            )
            logger.info(
                f"PostgreSQL Conversations: {verification_results['postgresql_conversations']['found']}/{verification_results['postgresql_conversations']['expected']} {verification_results['postgresql_conversations']['status']}"
            )
            logger.info(
                f"pgvector Embeddings: {verification_results['pgvector_embeddings']['found']}/{verification_results['pgvector_embeddings']['expected']} {verification_results['pgvector_embeddings']['status']}"
            )
            logger.info(
                f"Relationships: {verification_results['relationships']['found']}/{verification_results['relationships']['expected']} {verification_results['relationships']['status']}"
            )
            logger.info("=" * 60)

            # Check if all verifications passed
            all_passed = all(
                verification_results["neo4j_sessions"]["found"] >= 3,
                verification_results["postgresql_conversations"]["status"] == "✓",
                verification_results["pgvector_embeddings"]["status"] == "✓",
                verification_results["relationships"]["status"] == "✓",
            )

            if all_passed:
                logger.info("✅ All test data seeded successfully!")
                logger.info("Infrastructure is ready for integration testing.")
            else:
                logger.error("❌ Some test data seeding failed!")
                logger.error("Please check verification results above.")

        finally:
            # Close connections
            await self.close_connections()
            logger.info("Database connections closed")


async def main():
    """Main entry point."""
    settings = Settings()
    seeder = TestDataSeeder(settings)

    try:
        await seeder.run()
    except Exception as e:
        logger.error(f"Test data seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
