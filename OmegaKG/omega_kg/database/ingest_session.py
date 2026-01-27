from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from omega_kg.settings import settings

# Create async engine for Ingest Database
ingest_engine = create_async_engine(
    settings.ingest_database_url,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncIngestSessionLocal = async_sessionmaker(
    bind=ingest_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_ingest_db():
    """Dependency for getting an async session for Ingest DB."""
    async with AsyncIngestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
