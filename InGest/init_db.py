import asyncio
import logging
from ingest_llm_as.config import get_settings
from ingest_llm_as.core.saga_orchestrator import SagaOrchestrator
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    settings = get_settings()
    # Ensure compatible DSN for asyncpg
    dsn = settings.raw_db_url.replace("postgresql+asyncpg", "postgresql")

    logger.info(f"Connecting to database with DSN: {dsn}")

    # Initialize Saga (creates ingest_transactions)
    saga = SagaOrchestrator(postgres_dsn=dsn)
    await saga.create_saga_table()
    logger.info("Created ingest_transactions table.")

    # Initialize DLQ (creates ingest_failures)
    # Since we don't have a DLQ manager class handy with a create method exposed (checked via view_file earlier? maybe not explicit)
    # Let's just run the raw SQL here to be safe and quick.
    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ingest_failures (
                id SERIAL PRIMARY KEY,
                payload JSONB,
                error_message TEXT,
                correlation_id VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                status VARCHAR(20) DEFAULT 'NEW'
            )
        """)
        logger.info("Created ingest_failures table.")
    finally:
        await conn.close()

    logger.info("Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
