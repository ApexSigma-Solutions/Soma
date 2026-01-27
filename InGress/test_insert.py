"""Test raw_lake insert."""

import asyncio
import asyncpg
import json


async def test():
    conn = await asyncpg.connect("postgresql://omega_user:omega_dev_password@localhost:6000/omega_kg_stable")

    # Test insert
    query = """
        INSERT INTO raw_lake (source, event_type, payload, client_ip) 
        VALUES ($1, $2, $3, $4) 
        RETURNING id;
    """
    payload = {"command": "whoami", "output": "sigmadev11"}
    row_id = await conn.fetchval(query, "terminal", "command_log", json.dumps(payload), "127.0.0.1")
    print(f"Inserted row: {row_id}")

    # Verify
    row = await conn.fetchrow("SELECT * FROM raw_lake WHERE id = $1", row_id)
    print(f"Row: {dict(row)}")

    await conn.close()


asyncio.run(test())
