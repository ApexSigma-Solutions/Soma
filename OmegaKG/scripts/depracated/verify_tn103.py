import asyncio
import asyncpg


async def main():
    # Use the same connection string as in alembic.ini (or derived from settings)
    # We hardcoded it in alembic.ini for the fix, so let's use that.
    conn_str = "postgresql://omega_user:omega_dev_password@127.0.0.1:5433/omega_kg"

    try:
        conn = await asyncpg.connect(conn_str)
        print("Connected to Database.")

        # Check for table
        row = await conn.fetchrow(
            "SELECT to_regclass('public.raw_linear_events') as table_exists;"
        )

        if row and row["table_exists"]:
            print("SUCCESS: Table 'raw_linear_events' exists.")
        else:
            print("FAILURE: Table 'raw_linear_events' does NOT exist.")

        await conn.close()
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
