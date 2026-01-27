"""
Memory module for memOS.MCP ephemeral storage.

Provides Redis-backed working memory, scratchpad functionality,
and SimpleMem Stage 3 hybrid retrieval.
"""

from .redis_client import (
    RedisMemoryClient,
    MemoryEntry,
    PulseEvent,
    get_redis_client,
)
from .hybrid_retriever import (
    HybridRetriever,
    MemoryResult,
    RetrievalConfig,
    get_retriever,
)
from .loopback import (
    MemoryLoopback,
    LoopbackConfig,
    get_loopback,
)

__all__ = [
    # Redis working memory
    "RedisMemoryClient",
    "MemoryEntry",
    "PulseEvent",
    "get_redis_client",
    # SimpleMem Stage 3 retrieval
    "HybridRetriever",
    "MemoryResult",
    "RetrievalConfig",
    "get_retriever",
    # Loopback for saving (read-only constraint)
    "MemoryLoopback",
    "LoopbackConfig",
    "get_loopback",
]
