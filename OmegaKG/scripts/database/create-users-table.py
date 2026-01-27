"""
Create Users Table Migration

Creates the users table for authentication.
Run this script to initialize the users table in the database.
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from omega_kg.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
"""


async def create_users_table():
    """Create the users table in the database."""

    # Build async database URL
    db_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    )

    logger.info(
        f"Connecting to database: {settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    )

    engine = create_async_engine(db_url, echo=True)

    try:
        async with engine.begin() as conn:
            logger.info("Creating users table...")
            await conn.execute(text(CREATE_USERS_TABLE))
            logger.info("✓ Users table created successfully!")

            # Verify table creation
            result = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'users'"
                )
            )
            if result.fetchone():
                logger.info("✓ Verified: users table exists in database")
            else:
                logger.error("✗ Error: users table was not created")

    except Exception as e:
        logger.error(f"✗ Error creating users table: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_users_table())
