from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from omega_kg.settings import settings

# Async Engine
engine = create_async_engine(
    settings.database_url,
    echo=True,  # Set to False in production
    pool_pre_ping=True,
    future=True,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
