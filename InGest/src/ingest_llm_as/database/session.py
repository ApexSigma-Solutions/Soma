"""Database session management for InGest-LLM.as

This module provides both synchronous and asynchronous database sessions:
- Synchronous sessions for immediate raw persistence (atomic writes)
- Async sessions for background processing tasks
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from ..config import get_settings


def get_sync_engine():
    """Get synchronous database engine for raw persistence.

    CRITICAL: Uses psycopg2 driver for synchronous operations.
    This ensures atomic commits before returning HTTP responses.
    """
    settings = get_settings()
    # Convert asyncpg URL to psycopg2 for synchronous operations
    sync_url = settings.raw_db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return create_engine(
        sync_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def get_async_engine():
    """Get async database engine for background processing."""
    settings = get_settings()
    return create_async_engine(
        settings.raw_db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# Create session factories
sync_engine = get_sync_engine()
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)

async_engine = get_async_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_ingest_db() -> Generator[Session, None, None]:
    """Get synchronous database session for raw ingestion writes.

    CRITICAL: Must be synchronous to ensure atomic commit before
    returning HTTP response. Do NOT convert to async.

    Usage:
        @router.post("/ingest/text")
        async def ingest_text(
            request: IngestionRequest,
            db: Session = Depends(get_ingest_db),
        ):
            # Write to raw_ingestions table
            db.add(raw_record)
            db.commit()  # Synchronous commit
            return response

    Yields:
        Session: Synchronous SQLAlchemy session
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session() -> Generator[AsyncSession, None, None]:
    """Get async database session for background processing.

    Usage:
        async def process_ingestion(ingestion_id: str):
            async for session in get_async_session():
                # Process ingestion
                await session.commit()

    Yields:
        AsyncSession: Async SQLAlchemy session
    """
    async with AsyncSessionLocal() as session:
        yield session
