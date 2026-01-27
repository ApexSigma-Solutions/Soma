#!/usr/bin/env python3
"""Test app with scheduler added"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def dummy_job():
    """Dummy scheduled job"""
    logger.debug("Dummy job executed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Test lifespan with scheduler"""
    logger.info("[LIFESPAN] Startup phase starting...")

    # Initialize vector store
    from omega_kg.vector_store import get_vector_store

    logger.info("[LIFESPAN] Initializing vector store...")
    # initialize pool; no local variable needed
    await get_vector_store()
    logger.info("[LIFESPAN] ✓ Vector store initialized")

    # Start worker
    from omega_kg.workers.embedding_worker import start_worker, stop_worker

    logger.info("[LIFESPAN] Starting worker...")
    await start_worker()
    logger.info("[LIFESPAN] ✓ Worker started")

    # Add scheduler
    logger.info("[LIFESPAN] Starting scheduler...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(dummy_job, "interval", seconds=30, id="dummy_job")
    scheduler.start()
    logger.info("[LIFESPAN] ✓ Scheduler started")

    logger.info("[LIFESPAN] About to yield (startup complete)...")
    yield
    logger.info("[LIFESPAN] Yield returned (shutdown starting)...")

    # Shutdown
    logger.info("[LIFESPAN] Stopping scheduler...")
    scheduler.shutdown()
    logger.info("[LIFESPAN] ✓ Scheduler stopped")

    logger.info("[LIFESPAN] Stopping worker...")
    await stop_worker()
    logger.info("[LIFESPAN] ✓ Worker stopped")

    # Close pool
    from omega_kg.vector_store import VectorStore

    await VectorStore.close_pool()
    logger.info("[LIFESPAN] ✓ Vector store pool closed")
    logger.info("[LIFESPAN] Shutdown complete")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting scheduler test server on 127.0.0.1:8888...")
    uvicorn.run(app, host="127.0.0.1", port=8888)
