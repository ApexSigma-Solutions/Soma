import asyncio
from omega_kg.database.session import engine
from sqlalchemy import text


async def test_connection():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Database connection: OK")
    except Exception as e:
        print(f"Database connection error: {e}")
    finally:
        await engine.dispose()


asyncio.run(test_connection())
