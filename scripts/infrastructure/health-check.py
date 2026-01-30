#!/usr/bin/env python3
"""
Infrastructure Health Check Script
Tests connectivity to all memOS.MCP dependencies
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
import redis.asyncio as redis
from neo4j import GraphDatabase
import httpx


async def check_postgres():
    """Test PostgreSQL connection with pgvector"""
    try:
        conn = await asyncpg.connect(
            host="127.0.0.1",
            port=6000,
            user="omega_user",
            password="omega_dev_password",
            database="omega_kg_stable",
        )

        # Check if pgvector extension exists
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        )

        await conn.close()

        if result > 0:
            print("✅ PostgreSQL: Connected (pgvector enabled)")
            return True
        else:
            print("⚠️  PostgreSQL: Connected but pgvector not enabled")
            return False

    except Exception as e:
        print(f"❌ PostgreSQL: Connection failed - {e}")
        return False


async def check_redis():
    """Test Redis connection"""
    try:
        client = redis.from_url("redis://127.0.0.1:6380/0")
        await client.ping()
        await client.close()
        print("✅ Redis: Connected")
        return True
    except Exception as e:
        print(f"❌ Redis: Connection failed - {e}")
        return False


def check_neo4j():
    """Test Neo4j connection"""
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687", auth=("neo4j", "aDQUU5$@1dpuj5")
        )

        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()

        driver.close()
        print("✅ Neo4j: Connected")
        return True

    except Exception as e:
        print(f"❌ Neo4j: Connection failed - {e}")
        return False


async def check_ollama():
    """Test Ollama API"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            response.raise_for_status()

            data = response.json()
            models = [m["name"] for m in data.get("models", [])]

            if "bge-m3:latest" in models or "bge-m3" in models:
                print("✅ Ollama: Connected (bge-m3 model available)")
                return True
            else:
                print("⚠️  Ollama: Connected but bge-m3 model not found")
                print(f"   Available models: {', '.join(models)}")
                return False

    except Exception as e:
        print(f"❌ Ollama: Connection failed - {e}")
        return False


async def check_ingest_llm():
    """Test InGest-LLM service"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Try health endpoint first
            try:
                response = await client.get("http://localhost:8766/health")
                if response.status_code == 200:
                    print("✅ InGest-LLM: Connected on port 8766 (health check)")
                    return True
            except:
                pass

            # Fallback: try root endpoint
            response = await client.get("http://localhost:8766/")
            if response.status_code in [200, 404]:  # 404 is ok, means server is up
                print("✅ InGest-LLM: Connected on port 8766")
                return True

    except Exception as e:
        print(f"❌ InGest-LLM: Connection failed on port 8766 - {e}")
        return False


async def main():
    """Run all health checks"""
    print("\n" + "=" * 60)
    print("memOS.MCP Infrastructure Health Check")
    print("=" * 60 + "\n")

    results = {
        "PostgreSQL": await check_postgres(),
        "Redis": await check_redis(),
        "Neo4j": check_neo4j(),
        "Ollama": await check_ollama(),
        "InGest-LLM": await check_ingest_llm(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    total = len(results)
    passed = sum(results.values())

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✅ All services operational")
        return 0
    else:
        failed = [name for name, status in results.items() if not status]
        print(f"⚠️  Issues detected: {', '.join(failed)}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
