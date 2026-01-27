"""
Create Admin User Script

Creates an initial admin user for the CortexBridge application.
"""

import asyncio
import getpass
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


async def create_admin_user(
    email: str, username: str, password: str, full_name: str = "Administrator"
):
    """
    Create an admin user in the database.

    Args:
        email: Admin email address
        username: Admin username
        password: Admin password (will be hashed)
        full_name: Full name of the admin user
    """

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
                {"email": email, "username": username},
            )
            existing_user = result.fetchone()

            if existing_user:
                logger.warning(
                    f"⚠ User with email '{email}' or username '{username}' already exists!"
                )
                return False

            # Hash the password
            hashed_password = pwd_context.hash(password)

            # Insert the admin user
            await conn.execute(
                text("""
                    INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_verified)
                    VALUES (:email, :username, :hashed_password, :full_name, 'admin', TRUE, TRUE)
                """),
                {
                    "email": email,
                    "username": username,
                    "hashed_password": hashed_password,
                    "full_name": full_name,
                },
            )

            logger.info("✓ Admin user created successfully!")
            logger.info(f"  Email: {email}")
            logger.info(f"  Username: {username}")
            logger.info("  Role: admin")
            return True

    except Exception as e:
        logger.error(f"✗ Error creating admin user: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """Interactive script to create an admin user."""

    print("\n" + "=" * 60)
    print("CREATE ADMIN USER FOR CORTEXBRIDGE")
    print("=" * 60 + "\n")

    # Get user input
    email = input("Enter admin email: ").strip()
    username = input("Enter admin username: ").strip()
    full_name = (
        input("Enter full name (optional, press Enter to skip): ").strip()
        or "Administrator"
    )

    # Get password securely
    while True:
        password = getpass.getpass("Enter password (min 8 characters): ")
        if len(password) < 8:
            print("⚠ Password must be at least 8 characters long. Try again.")
            continue

        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("⚠ Passwords do not match. Try again.")
            continue

        break

    print("\n" + "-" * 60)
    print("Creating admin user...")
    print("-" * 60 + "\n")

    success = await create_admin_user(email, username, password, full_name)

    if success:
        print("\n" + "=" * 60)
        print("✓ ADMIN USER CREATED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now login to CortexBridge at http://localhost:6001")
        print(f"  Email: {email}")
        print("  Password: [the password you just entered]")
        print("\n")
    else:
        print("\n" + "=" * 60)
        print("✗ FAILED TO CREATE ADMIN USER")
        print("=" * 60)
        print("\nPlease check the logs above for details.\n")


if __name__ == "__main__":
    asyncio.run(main())
