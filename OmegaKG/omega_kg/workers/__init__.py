"""
Background workers for async processing.

Includes:
- embedding_worker: Async polling worker for vector embedding generation
- stream_consumer: Redis stream consumer for Soma working memory
"""

from .stream_consumer import (
    StreamConsumer,
    get_stream_consumer,
    start_stream_consumer,
    stop_stream_consumer,
)

__all__: list[str] = [
    "StreamConsumer",
    "get_stream_consumer",
    "start_stream_consumer",
    "stop_stream_consumer",
]
