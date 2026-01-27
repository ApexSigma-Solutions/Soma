"""Check if users exist in database."""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from omega_kg.settings import settings


async def check_users():
    db_url = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id, email, username, role, is_active FROM users")
        )
        users = result.fetchall()

        print(f"\nFound {len(users)} user(s) in database:\n")
        for user in users:
            print(f"  ID: {user[0]}")
            print(f"  Email: {user[1]}")
            print(f"  Username: {user[2]}")
            print(f"  Role: {user[3]}")
            print(f"  Active: {user[4]}")
            print()

    await engine.dispose()


asyncio.run(check_users())
