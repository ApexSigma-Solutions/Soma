import asyncio
import os
import asyncpg
from tabulate import tabulate

PG_DSN = os.getenv(
    "SOMA_PG_DSN",
    "postgresql://soma_user:qwHdAhk3Qu5DLFtY2oEOaXCnmBb9lSGI@localhost:6000/soma_sensory_lake",
)


async def check_schema():
    print(f"Connecting to {PG_DSN}...")
    try:
        conn = await asyncpg.connect(PG_DSN)
        rows = await conn.fetch("""
            SELECT column_name, data_type, udt_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'raw_lake'
            ORDER BY ordinal_position;
        """)

        # Convert to list of lists for tabulate, ensuring strings
        table_data = []
        for r in rows:
            default_val = (
                str(r["column_default"]) if r["column_default"] is not None else "None"
            )
            table_data.append(
                [
                    r["column_name"],
                    r["data_type"],
                    r["udt_name"],
                    r["is_nullable"],
                    default_val,
                ]
            )

        print("\n=== raw_lake Columns ===")
        if table_data:
            print(
                tabulate(
                    table_data,
                    headers=["Column", "Type", "UDT", "Nullable", "Default"],
                    tablefmt="grid",
                )
            )
        else:
            print("No columns found! Table might not exist.")

        # Check Enum
        enums = await conn.fetch(
            "SELECT typname FROM pg_type WHERE typname = 'raw_lake_status'"
        )
        print(f"\nEnum 'raw_lake_status' exists: {len(enums) > 0}")  # Should be 1

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_schema())
