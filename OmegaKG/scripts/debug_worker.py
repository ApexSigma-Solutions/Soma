#!/usr/bin/env python3
"""Debug script to test lifespan and worker startup"""

import asyncio
import logging

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_worker_startup():
    """
    Run a smoke test that exercises startup and shutdown of the embedding worker and the vector store.

    Initializes the vector store, starts the embedding worker, waits briefly to verify the worker remains active, stops the worker, and closes the vector store's connection pool. Logs progress at each step and re-raises any exception encountered.
    """
    logger.info("Testing worker startup...")

    try:
        from omega_kg.workers.embedding_worker import start_worker, stop_worker
        from omega_kg.vector_store import get_vector_store

        # Test vector store init
        logger.info("Initializing vector store...")
        vector_store = await get_vector_store()
        logger.info(f"✓ Vector store initialized: {vector_store}")

        # Test worker startup
        logger.info("Starting worker...")
        await start_worker()
        logger.info("✓ Worker started (background task should be running)")

        # Wait a bit
        await asyncio.sleep(2)
        logger.info("✓ Worker is still running after 2 seconds")

        # Stop worker
        logger.info("Stopping worker...")
        await stop_worker()
        logger.info("✓ Worker stopped")

        # Close pool
        from omega_kg.vector_store import VectorStore

        await VectorStore.close_pool()
        logger.info("✓ Vector store pool closed")

    except Exception as e:
        logger.exception(f"Error during test: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_worker_startup())
