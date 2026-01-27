"""
Quick Create Admin User

Non-interactive script to quickly create an admin user.
Edit the credentials below and run this script.
"""

import asyncio
import logging
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from omega_kg.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# EDIT THESE CREDENTIALS
# ============================================================================
ADMIN_EMAIL = "admin@omegakg.io"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin2026"  # bcrypt has 72 char limit
ADMIN_FULL_NAME = "Omega Administrator"
# ============================================================================


async def create_admin():
    """Create admin user with predefined credentials."""

    # Build async database URL
    db_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    )

    logger.info(
        f"Connecting to database: {settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    )

    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Check if user already exists
            result = await conn.execute(
                text(
                    "SELECT id FROM users WHERE email = :email OR username = :username"
                ),
                {"email": ADMIN_EMAIL, "username": ADMIN_USERNAME},
            )
            existing_user = result.fetchone()

            if existing_user:
                logger.warning(
                    f"⚠ User with email '{ADMIN_EMAIL}' or username '{ADMIN_USERNAME}' already exists!"
                )
                logger.info(
                    "If you want to create a new user, change the credentials at the top of this script."
                )
                return False

            # Hash the password
            hashed_password = pwd_context.hash(ADMIN_PASSWORD)

            # Insert the admin user
            await conn.execute(
                text("""
                    INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_verified)
                    VALUES (:email, :username, :hashed_password, :full_name, 'admin', TRUE, TRUE)
                """),
                {
                    "email": ADMIN_EMAIL,
                    "username": ADMIN_USERNAME,
                    "hashed_password": hashed_password,
                    "full_name": ADMIN_FULL_NAME,
                },
            )

            logger.info("\n" + "=" * 60)
            logger.info("✓ ADMIN USER CREATED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info("\nLogin to CortexBridge at http://localhost:6001")
            logger.info(f"  Email: {ADMIN_EMAIL}")
            logger.info(f"  Password: {ADMIN_PASSWORD}")
            logger.info("\n⚠ IMPORTANT: Change the password after first login!\n")
            return True

    except Exception as e:
        logger.error(f"✗ Error creating admin user: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
