"""Database adapters for dependency injection.

This module provides dependency functions for database connections
used in FastAPI route handlers.
"""

from typing import AsyncGenerator

from neo4j import AsyncDriver
import asyncpg

from ..database.graph import graph_driver
from ..settings import get_settings


async def get_neo4j_driver() -> AsyncDriver:
    """Get Neo4j async driver for dependency injection.

    Returns:
        AsyncDriver: Neo4j async driver instance
    """
    if graph_driver._driver is None:
        await graph_driver.connect()

    if graph_driver._driver is None:
        raise RuntimeError("Failed to connect to Neo4j")

    return graph_driver._driver


async def get_pg_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Get PostgreSQL connection pool for dependency injection.

    Yields:
        asyncpg.Pool: PostgreSQL connection pool
    """
    settings = get_settings()

    # Create connection pool
    pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
    )

    try:
        yield pool
    finally:
        await pool.close()
