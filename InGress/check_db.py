"""Quick DB check script."""

import asyncio
import asyncpg


async def check():
    conn = await asyncpg.connect("postgresql://omega_user:omega_dev_password@localhost:6000/omega_kg_stable")

    # Check tables
    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('raw_lake', 'alembic_version')"
    )
    print("Tables found:", [r["table_name"] for r in tables])

    # Check alembic version
    if any(r["table_name"] == "alembic_version" for r in tables):
        ver = await conn.fetch("SELECT version_num FROM alembic_version")
        print("Alembic versions:", [r["version_num"] for r in ver])

    await conn.close()


asyncio.run(check())
