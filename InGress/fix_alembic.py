"""Fix alembic version and create raw_lake table."""

import asyncio
import asyncpg


async def fix():
    conn = await asyncpg.connect("postgresql://omega_user:omega_dev_password@localhost:6000/omega_kg_stable")

    # Clear stale alembic version from InGest
    print("Clearing stale alembic version...")
    await conn.execute("DELETE FROM alembic_version WHERE version_num = '7e2f3204cf8e'")

    # Verify
    ver = await conn.fetch("SELECT version_num FROM alembic_version")
    print("Alembic versions after clear:", [r["version_num"] for r in ver])

    await conn.close()
    print("Done. Now run: alembic upgrade head")


asyncio.run(fix())
