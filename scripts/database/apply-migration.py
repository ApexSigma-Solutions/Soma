import asyncio
import os
import asyncpg

# Config
PG_DSN = os.getenv(
    "SOMA_PG_DSN",
    "postgresql://soma_user:qwHdAhk3Qu5DLFtY2oEOaXCnmBb9lSGI@localhost:6000/soma_sensory_lake",
)
MIGRATION_FILE = r"d:\projects\Soma\InGress\schema\002_add_processing_status.sql"


async def apply_migration():
    if not os.path.exists(MIGRATION_FILE):
        print(f"Error: Migration file not found at {MIGRATION_FILE}")
        return

    print(f"Reading migration file: {MIGRATION_FILE}")
    with open(MIGRATION_FILE, "r") as f:
        sql = f.read()

    print("Connecting to DB...")
    try:
        conn = await asyncpg.connect(PG_DSN)
        print("Applying migration...")

        # Split into statements if needed, or execute as block if supported.
        # asyncpg execute supports multiple statements in one string usually.
        await conn.execute(sql)

        print("Migration applied successfully!")

        # Verify
        enums = await conn.fetch(
            "SELECT typname FROM pg_type WHERE typname = 'raw_lake_status'"
        )
        print(f"Verification - Enum 'raw_lake_status' exists: {len(enums) > 0}")

        await conn.close()
    except Exception as e:
        print(f"Error applying migration: {e}")


if __name__ == "__main__":
    asyncio.run(apply_migration())
