#!/usr/bin/env python3
"""
Test script to verify InGest-LLM connection configurations.
This script tests PostgreSQL, Neo4j, and Redis connections.
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ingest_llm_as.config import get_settings
from ingest_llm_as.services.neo4j_service import Neo4jService
import asyncpg
import redis.asyncio as redis


async def test_postgresql_connection():
    """Test PostgreSQL connection."""
    print("Testing PostgreSQL connection...")
    settings = get_settings()

    try:
        # Use the corrected connection string format
        db_url = settings.raw_db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)

        # Test a simple query
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        if result == 1:
            print("[OK] PostgreSQL connection successful")
            return True
        else:
            print("[FAIL] PostgreSQL connection failed: unexpected result")
            return False
    except Exception as e:
        print(f"[FAIL] PostgreSQL connection failed: {e}")
        return False


async def test_neo4j_connection():
    """Test Neo4j connection."""
    print("Testing Neo4j connection...")
    settings = get_settings()

    try:
        neo4j_service = Neo4jService()

        # Test by creating a temporary node and deleting it
        test_id = "test_connection_123"
        node_id = neo4j_service.create_chat_session(
            source_id=test_id, platform="test", filepath="/tmp/test", message_count=1
        )

        if node_id:
            print("[OK] Neo4j connection successful")
            # Clean up test node
            with neo4j_service.driver.session() as session:
                session.run(
                    "MATCH (n:ChatSession {conversation_hash: $id}) DETACH DELETE n",
                    id=test_id,
                )
            neo4j_service.close()
            return True
        else:
            print("[FAIL] Neo4j connection failed: could not create node")
            neo4j_service.close()
            return False
    except Exception as e:
        print(f"[FAIL] Neo4j connection failed: {e}")
        try:
            neo4j_service.close()
        except:
            pass
        return False


async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")
    settings = get_settings()

    try:
        # Try to connect to Redis (port 6379)
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        await r.ping()
        await r.aclose()
        print("[OK] Redis connection successful")
        return True
    except Exception as e:
        print(f"[FAIL] Redis connection failed: {e}")
        return False


async def main():
    """Main test function."""
    print("InGest-LLM Connection Test")
    print("=" * 40)

    # Load settings
    settings = get_settings()
    print("Using settings:")
    print(f"  PostgreSQL: {settings.raw_db_url}")
    print(f"  Neo4j URI: {settings.neo4j_uri}")
    print(f"  Neo4j User: {settings.neo4j_user}")
    print(f"  Neo4j Password: {'*' * len(settings.neo4j_password)}")
    print()

    # Run tests
    results = []
    results.append(await test_postgresql_connection())
    results.append(await test_neo4j_connection())
    results.append(await test_redis_connection())

    print()
    print("=" * 40)
    if all(results):
        print("[SUCCESS] All connections successful!")
        return 0
    else:
        print("[WARNING] Some connections failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
