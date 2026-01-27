import asyncio
from omega_kg.database.session import engine
from sqlalchemy import text


async def check_table():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT to_regclass('raw_webhook_events')"))
        table_exists = result.scalar()
        print(f"Table exists: {table_exists is not None}")
    await engine.dispose()


asyncio.run(check_table())
