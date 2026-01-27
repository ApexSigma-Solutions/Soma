"""
Direct bcrypt admin creator - bypasses passlib
"""

import asyncio
import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from omega_kg.settings import settings

ADMIN_EMAIL = "admin@omegakg.io"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_FULL_NAME = "Administrator"


async def create_admin():
    """Create admin using direct bcrypt."""

    # Hash password with bcrypt directly
    password_bytes = ADMIN_PASSWORD.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    hashed_str = hashed.decode("utf-8")

    print("Password hashed successfully")

    # Connect to database
    db_url = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Check existing
            result = await conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": ADMIN_EMAIL},
            )
            if result.fetchone():
                print(f"User {ADMIN_EMAIL} already exists!")
                return

            # Insert
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
                    "password": hashed_str,
                    "name": ADMIN_FULL_NAME,
                },
            )

            print("\n" + "=" * 60)
            print("✓ ADMIN USER CREATED SUCCESSFULLY!")
            print("=" * 60)
            print("\nLogin at: http://localhost:6001")
            print(f"Email:    {ADMIN_EMAIL}")
            print(f"Password: {ADMIN_PASSWORD}")
            print()

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
