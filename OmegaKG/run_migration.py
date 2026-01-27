import asyncio
from alembic.config import Config
from alembic import command


async def run_migration():
    config = Config("alembic.ini")
    try:
        command.upgrade(config, "head")
        print("Migration completed")
    except Exception as e:
        print(f"Migration error: {e}")
        import traceback

        traceback.print_exc()


asyncio.run(run_migration())
