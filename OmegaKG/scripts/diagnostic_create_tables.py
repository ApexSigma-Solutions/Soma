#!/usr/bin/env python3
"""
Create missing database tables
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega_kg.database.session import engine
from omega_kg.models import Base


async def create_tables():
    """Create all database tables."""
    print("=" * 60)
    print("Creating Database Tables")
    print("=" * 60)

    try:
        async with engine.begin() as conn:
            print("Creating tables via Base.metadata.create_all()...")
            await conn.run_sync(Base.metadata.create_all)
            print("[OK] Tables created successfully")

        # Verify tables
        from sqlalchemy import text

        async with engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            )
            tables = result.fetchall()
            print(f"\nDatabase tables ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")

            # Check for raw_linear_events specifically
            result = await conn.execute(
                text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'raw_linear_events'
                )
            """)
            )
            exists = result.scalar()

            if exists:
                print("\n[OK] raw_linear_events table exists")
            else:
                print("\n[FAIL] raw_linear_events table still missing")

        return 0
    except Exception as e:
        print(f"[FAIL] Error creating tables: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(create_tables()))
