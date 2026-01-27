import asyncio
import logging
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
sys.path.append(".")

from omega_kg.settings import settings
from omega_kg.database.base import Base
# Import models to register them with Base.metadata

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_ingest_db")


async def init_db():
    """Initialize Ingest Database tables."""
    ingest_url = settings.ingest_database_url
    logger.info(f"Connecting to Ingest DB: {ingest_url.split('@')[-1]}")  # Mask auth

    engine = create_async_engine(ingest_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Ensuring pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Check if raw_ingestions table exists (managed by InGest-LLM)
        result = await conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'raw_ingestions'
            )
        """)
        )
        raw_ingestions_exists = result.scalar()

        if raw_ingestions_exists:
            logger.info("✓ raw_ingestions table exists (managed by InGest-LLM)")
        else:
            logger.warning(
                "⚠ raw_ingestions table not found. Run InGest-LLM migrations first:"
            )
            logger.warning("  cd InGest-LLM.as && alembic upgrade head")

        logger.info("Creating OmegaKG tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
