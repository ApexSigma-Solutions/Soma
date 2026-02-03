"""Vector Index Worker - Standalone entry point for OmegaKG stream consumer.

Provides a standalone entry for running the stream consumer as a worker process.
Re-exports from stream_consumer.py for clarity per TN-SOMA-205.

Usage:
    python -m omega_kg.workers.vector_index_worker

Or via orchestrator:
    python orchestrator.py start omegakg-worker
"""

from omega_kg.workers.stream_consumer import (
    StreamConsumer,
    get_stream_consumer,
    start_stream_consumer,
    stop_stream_consumer,
)

__all__ = [
    "StreamConsumer",
    "get_stream_consumer",
    "start_stream_consumer",
    "stop_stream_consumer",
]

if __name__ == "__main__":
    import asyncio
    import structlog

    log = structlog.get_logger()
    log.info("vector_index_worker_starting", stream="soma:digestion:stream")

    consumer = StreamConsumer()
    try:
        asyncio.run(consumer.start())
    except KeyboardInterrupt:
        log.info("vector_index_worker_shutdown", reason="user_interrupt")
