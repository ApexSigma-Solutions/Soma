"""
Simple Admin User Creator

Uses the existing auth_utils to create an admin user.
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from omega_kg.settings import settings
from omega_kg.auth_utils import get_password_hash

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Credentials
ADMIN_EMAIL = "admin@omegakg.io"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Simple password for testing
ADMIN_FULL_NAME = "Administrator"


async def create_admin():
    """Create admin user."""

    db_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    )

    logger.info("Connecting to database...")
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Check if user exists
            result = await conn.execute(
                text("SELECT id, email FROM users WHERE email = :email"),
                {"email": ADMIN_EMAIL},
            )
            existing = result.fetchone()

            if existing:
                logger.warning(f"User already exists: {ADMIN_EMAIL}")
                return False

            # Hash password using auth_utils
            logger.info("Hashing password...")
            hashed_pw = get_password_hash(ADMIN_PASSWORD)

            # Insert user
            logger.info("Creating admin user...")
            await conn.execute(
                text("""
                    INSERT INTO users 
                    (email, username, hashed_password, full_name, role, is_active, is_verified)
                    VALUES 
                    (:email, :username, :password, :name, 'admin', true, true)
                """),
                {
                    "email": ADMIN_EMAIL,
                    "username": ADMIN_USERNAME,
                    "password": hashed_pw,
                    "name": ADMIN_FULL_NAME,
                },
            )

            print("\n" + "=" * 60)
            print("✓ ADMIN USER CREATED!")
            print("=" * 60)
            print("\nLogin at: http://localhost:6001")
            print(f"Email:    {ADMIN_EMAIL}")
            print(f"Password: {ADMIN_PASSWORD}")
            print("\n")
            return True

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
