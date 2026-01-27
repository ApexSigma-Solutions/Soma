import os
import asyncio
import asyncpg
from dotenv import load_dotenv

# Load env directly to be sure
load_dotenv("D:/projects/OmegaKG/InGest-LLM.as/.env")
dsn = os.getenv("POSTGRES_DSN")

print(f"Testing connection to: {dsn}")


async def test_conn():
    try:
        # Convert standard DSN to asyncpg format if needed, but asyncpg.connect handles postgres:// often
        # However, asyncpg strictly usually wants standard url.
        # Let's try connecting.
        conn = await asyncpg.connect(dsn)
        print("✅ Connection Successful!")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_conn())
