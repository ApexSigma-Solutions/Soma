#!/usr/bin/env python3
"""Query PostgreSQL to check embedding status"""

import asyncio
import asyncpg
from omega_kg.config import (
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_DB,
    POSTGRES_SERVER,
    POSTGRES_PORT,
)


async def check_embeddings():
    """
    Check the embedding records in the omega_vectors_1024 PostgreSQL table and print a brief report.

    Queries the database for the latest five rows (id, message_id, node_label, status, retry_count, created_at, updated_at) and prints each row if present; then retrieves and prints an aggregation of counts grouped by status. Establishes and closes a PostgreSQL connection as part of its operation.
    """
    conn = await asyncpg.connect(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        host=POSTGRES_SERVER,
        port=POSTGRES_PORT,
    )

    print("=" * 70)
    print("CHECKING POSTGRESQL EMBEDDINGS")
    print("=" * 70)

    # Get latest records
    rows = await conn.fetch(
        """
        SELECT id, message_id, node_label, status, retry_count,
               created_at, updated_at
        FROM omega_vectors_1024
        ORDER BY id DESC
        LIMIT 5
    """
    )

    if not rows:
        print("\n✗ No records found in omega_vectors_1024 table")
    else:
        print(f"\n✓ Found {len(rows)} record(s):\n")
        for row in rows:
            print(f"  ID: {row['id']}")
            print(f"  Message ID (Neo4j): {row['message_id']}")
            print(f"  Node Label: {row['node_label']}")
            print(f"  Status: {row['status']}")
            print(f"  Retry Count: {row['retry_count']}")
            print(f"  Created: {row['created_at']}")
            print(f"  Updated: {row['updated_at']}")
            print("  " + "-" * 66)

    # Get count by status
    stats = await conn.fetch(
        """
        SELECT status, COUNT(*) as count
        FROM omega_vectors_1024
        GROUP BY status
    """
    )

    if stats:
        print("\nStatus Summary:")
        for stat in stats:
            print(f"  {stat['status']}: {stat['count']}")

    await conn.close()
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(check_embeddings())
