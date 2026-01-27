"""Check raw_lake records status."""

import asyncio
import asyncpg


async def check():
    conn = await asyncpg.connect("postgresql://omega_user:omega_dev_password@localhost:6000/omega_kg_stable")

    rows = await conn.fetch("SELECT id, source, event_type, processed FROM raw_lake ORDER BY ingested_at DESC LIMIT 10")
    print(f"Found {len(rows)} records:")
    for row in rows:
        print(f"  {row['id']} | {row['source']:10} | {row['event_type']:15} | processed={row['processed']}")

    await conn.close()


asyncio.run(check())
