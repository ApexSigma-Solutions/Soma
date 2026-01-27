"""
memOS.MCP Infrastructure Health Check

Verifies that all required services are running and accessible:
- Redis (ephemeral memory)
- Ollama (embeddings)
- PostgreSQL (persistent storage)
"""

import asyncio
import sys
from typing import Tuple

# Test imports
try:
    import redis
    import httpx
    import asyncpg
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   Run: poetry install")
    sys.exit(1)


async def check_redis(host: str = "localhost", port: int = 6379) -> Tuple[bool, str]:
    """Check Redis connectivity."""
    try:
        client = redis.Redis(host=host, port=port, socket_connect_timeout=3)
        result = client.ping()
        if result:
            info = client.info("server")
            version = info.get("redis_version", "unknown")
            return True, f"Connected (v{version})"
        return False, "Ping failed"
    except redis.ConnectionError:
        return False, "Connection refused - is Redis running?"
    except Exception as e:
        return False, str(e)


async def check_ollama(base_url: str = "http://localhost:11434") -> Tuple[bool, str]:
    """Check Ollama connectivity and model availability."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check API endpoint
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()

            # Check for bge-m3 model
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]

            has_bge_m3 = any("bge-m3" in name for name in model_names)

            if has_bge_m3:
                return True, f"Connected ({len(models)} models, bge-m3 ready)"
            else:
                return True, f"Connected ({len(models)} models, ⚠️ bge-m3 not found)"

    except httpx.ConnectError:
        return False, "Connection refused - is Ollama running?"
    except httpx.HTTPStatusError as e:
        return False, f"HTTP {e.response.status_code}"
    except Exception as e:
        return False, str(e)


async def check_postgres(
    host: str = "localhost",
    port: int = 5800,
    user: str = "omega_user",
    password: str = "omega_secure_password_change_me",
    database: str = "omega_kg_stable",
) -> Tuple[bool, str]:
    """Check PostgreSQL connectivity and pgvector extension."""
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            timeout=5,
        )

        # Check pgvector extension
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )

        # Check memos schema
        schema_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'memos')"
        )

        await conn.close()

        if result and schema_exists:
            return True, "Connected (pgvector enabled, memos schema ready)"
        elif result:
            return True, "Connected (pgvector enabled, ⚠️ memos schema missing)"
        else:
            return True, "Connected (⚠️ pgvector extension missing)"

    except asyncpg.InvalidPasswordError:
        return False, "Authentication failed - check credentials"
    except asyncpg.CannotConnectNowError:
        return False, "Connection refused - is PostgreSQL running?"
    except Exception as e:
        return False, str(e)


async def main():
    """Run all health checks."""
    print("=" * 80)
    print(" memOS.MCP Infrastructure Health Check")
    print("=" * 80)
    print()

    # Load environment if available
    try:
        from memos_mcp.config import settings

        redis_host = settings.redis_host
        redis_port = settings.redis_port
        ollama_url = settings.ollama_base_url
        pg_host = settings.postgres_host
        pg_port = settings.postgres_port
        pg_user = settings.postgres_user
        pg_password = settings.postgres_password
        pg_db = settings.postgres_db
    except Exception:
        # Use defaults
        redis_host = "localhost"
        redis_port = 6379
        ollama_url = "http://localhost:11434"
        pg_host = "localhost"
        pg_port = 5800
        pg_user = "omega_user"
        pg_password = "omega_secure_password_change_me"
        pg_db = "omega_kg_stable"

    all_healthy = True

    # Check Redis
    print("📦 Redis (Ephemeral Memory)")
    print(f"   Endpoint: redis://{redis_host}:{redis_port}")
    redis_ok, redis_msg = await check_redis(redis_host, redis_port)
    if redis_ok:
        print(f"   Status:   ✅ {redis_msg}")
    else:
        print(f"   Status:   ❌ {redis_msg}")
        all_healthy = False
    print()

    # Check Ollama
    print("🤖 Ollama (Embeddings)")
    print(f"   Endpoint: {ollama_url}")
    ollama_ok, ollama_msg = await check_ollama(ollama_url)
    if ollama_ok:
        print(f"   Status:   ✅ {ollama_msg}")
    else:
        print(f"   Status:   ❌ {ollama_msg}")
        all_healthy = False
    print()

    # Check PostgreSQL
    print("🗄️  PostgreSQL (Persistent Storage)")
    print(f"   Endpoint: postgresql://{pg_user}@{pg_host}:{pg_port}/{pg_db}")
    pg_ok, pg_msg = await check_postgres(pg_host, pg_port, pg_user, pg_password, pg_db)
    if pg_ok:
        print(f"   Status:   ✅ {pg_msg}")
    else:
        print(f"   Status:   ❌ {pg_msg}")
        all_healthy = False
    print()

    # Summary
    print("=" * 80)
    if all_healthy:
        print("✅ All services healthy - memOS.MCP ready to start")
        print()
        print("Next steps:")
        print("  1. Start memOS: poetry run python -m memos_mcp --sse")
        print("  2. Test endpoint: curl http://localhost:8768/health")
        return 0
    else:
        print("❌ Some services are not healthy")
        print()
        print("To start services:")
        print("  Windows: .\\start-memos.ps1")
        print("  Linux:   docker-compose up -d")
        print()
        print("For detailed setup: See INFRASTRUCTURE_SETUP.md")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
