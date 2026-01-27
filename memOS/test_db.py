import asyncio
import asyncpg
from memos_mcp.config import settings


async def test_connect():
    print(
        f"Connecting to {settings.postgres_host}:{settings.postgres_port} as {settings.postgres_user} db={settings.postgres_db}"
    )
    dsn = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    print(f"DSN: {dsn}")
    try:
        conn = await asyncpg.connect(dsn)
        print("Connected successfully!")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_connect())
