"""
Neo4j Async Graph Driver

Singleton wrapper for Neo4j async driver with connection pooling.
Phase 6: TN-LINEAR-06 - Graph Topology
"""

import logging
from contextlib import asynccontextmanager

from neo4j import AsyncDriver, AsyncGraphDatabase

from omega_kg.settings import settings

logger = logging.getLogger(__name__)


class AsyncGraphDriver:
    """
    Singleton wrapper for the Neo4j Async Driver.
    Handles connection pooling and session management.
    """

    _instance = None
    _driver: AsyncDriver | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncGraphDriver, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        """Initializes the Neo4j driver if not already connected."""
        if self._driver is None:
            try:
                # Using lowercase settings as per codebase convention
                self._driver = AsyncGraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                await self._driver.verify_connectivity()
                logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                self._driver = None
                raise

    async def close(self):
        """Closes the driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed.")

    @asynccontextmanager
    async def session(self):
        """
        Async Context Manager for a Neo4j Session.
        Defaulting to 'neo4j' database explicitly.
        """
        if self._driver is None:
            await self.connect()

        driver = self._driver
        if driver is None:
            raise RuntimeError("Neo4j driver not initialized")

        async with driver.session(database="neo4j") as session:
            yield session

    async def verify_connectivity(self) -> bool:
        """Checks if the database is reachable."""
        try:
            if self._driver is None:
                await self.connect()
            driver = self._driver
            if driver is None:
                return False
            await driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {e}")
            return False


# Global instance
graph_driver = AsyncGraphDriver()
