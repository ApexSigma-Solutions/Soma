import asyncio
from omega_kg.database.session import engine
from sqlalchemy import text


async def check_alembic():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            versions = result.fetchall()
            print(f"Current alembic versions: {versions}")
    except Exception as e:
        print(f"Error checking alembic version: {e}")
    finally:
        await engine.dispose()


asyncio.run(check_alembic())
