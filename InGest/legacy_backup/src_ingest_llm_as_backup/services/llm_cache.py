"""
Redis-based LLM Cache Service

This service provides efficient caching for LLM prompts and responses
to optimize costs and improve performance across the ApexSigma ecosystem.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    prompt_hash: str
    response: str
    model: str
    timestamp: datetime
    token_count: int
    cost_estimate: float
    metadata: Dict[str, Any]
    ttl_seconds: int = 3600  # 1 hour default

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary loaded from Redis."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class CacheStats:
    """Cache statistics."""

    total_entries: int
    hit_rate: float
    total_cost_saved: float
    total_tokens_saved: int
    cache_size_mb: float
    oldest_entry: Optional[datetime]
    newest_entry: Optional[datetime]


class LLMCache:
    """
    Redis-based LLM cache for prompt optimization.

    Features:
    - Prompt deduplication based on semantic hashing
    - Configurable TTL per model/use case
    - Cost tracking and optimization metrics
    - Automatic cache cleanup and rotation
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "apexsigma:llm_cache:",
        default_ttl: int = 3600,
        max_cache_size_mb: float = 100.0,
    ):
        """Initialize the LLM cache."""
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.max_cache_size_mb = max_cache_size_mb
        self.logger = get_logger(__name__)

        # Redis client (will be initialized in connect)
        self.redis_client = None

        # Stats tracking
        self.hits = 0
        self.misses = 0
        self.total_cost_saved = 0.0
        self.total_tokens_saved = 0

    async def connect(self) -> bool:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis library not available, cache disabled")
            return False

        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            self.logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False

    def _generate_cache_key(
        self, prompt: str, model: str, metadata: Dict[str, Any] = None
    ) -> str:
        """Generate a cache key for the prompt."""

        # Create a hash based on prompt content and model
        content = f"{model}:{prompt}"

        # Include relevant metadata in the hash
        if metadata:
            # Only include stable metadata that affects the response
            stable_metadata = {
                k: v
                for k, v in metadata.items()
                if k in ["temperature", "max_tokens", "top_p", "system_prompt"]
            }
            content += f":{json.dumps(stable_metadata, sort_keys=True)}"

        # Generate SHA-256 hash
        prompt_hash = hashlib.sha256(content.encode()).hexdigest()

        return f"{self.key_prefix}{prompt_hash}"

    async def get(
        self, prompt: str, model: str, metadata: Dict[str, Any] = None
    ) -> Optional[CacheEntry]:
        """Get cached response for a prompt."""

        if not self.redis_client:
            return None

        cache_key = self._generate_cache_key(prompt, model, metadata)

        try:
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                entry_dict = json.loads(cached_data)
                entry = CacheEntry.from_dict(entry_dict)

                # Update stats
                self.hits += 1
                self.total_cost_saved += entry.cost_estimate
                self.total_tokens_saved += entry.token_count

                self.logger.debug(f"Cache hit for model {model}")
                return entry
            else:
                self.misses += 1
                self.logger.debug(f"Cache miss for model {model}")
                return None

        except Exception as e:
            self.logger.error(f"Error retrieving from cache: {e}")
            return None

    async def set(
        self,
        prompt: str,
        response: str,
        model: str,
        token_count: int,
        cost_estimate: float = 0.0,
        metadata: Dict[str, Any] = None,
        ttl_seconds: int = None,
    ) -> bool:
        """Cache a prompt-response pair."""

        if not self.redis_client:
            return False

        cache_key = self._generate_cache_key(prompt, model, metadata)
        ttl = ttl_seconds or self.default_ttl

        try:
            entry = CacheEntry(
                prompt_hash=cache_key.replace(self.key_prefix, ""),
                response=response,
                model=model,
                timestamp=datetime.now(),
                token_count=token_count,
                cost_estimate=cost_estimate,
                metadata=metadata or {},
                ttl_seconds=ttl,
            )

            # Store in Redis with TTL
            await self.redis_client.setex(cache_key, ttl, json.dumps(entry.to_dict()))

            self.logger.debug(f"Cached response for model {model} (TTL: {ttl}s)")

            # Check cache size and cleanup if needed
            await self._cleanup_if_needed()

            return True

        except Exception as e:
            self.logger.error(f"Error storing in cache: {e}")
            return False

    async def delete(
        self, prompt: str, model: str, metadata: Dict[str, Any] = None
    ) -> bool:
        """Delete a cached entry."""

        if not self.redis_client:
            return False

        cache_key = self._generate_cache_key(prompt, model, metadata)

        try:
            result = await self.redis_client.delete(cache_key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Error deleting from cache: {e}")
            return False

    async def clear_model_cache(self, model: str) -> int:
        """Clear all cached entries for a specific model."""

        if not self.redis_client:
            return 0

        try:
            # Find all keys for this model
            pattern = f"{self.key_prefix}*"
            keys = []

            async for key in self.redis_client.scan_iter(match=pattern):
                # Check if this key belongs to the specified model
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    entry_dict = json.loads(cached_data)
                    if entry_dict.get("model") == model:
                        keys.append(key)

            # Delete all found keys
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self.logger.info(f"Cleared {deleted} cache entries for model {model}")
                return deleted

            return 0

        except Exception as e:
            self.logger.error(f"Error clearing model cache: {e}")
            return 0

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""

        if not self.redis_client:
            return CacheStats(0, 0.0, 0.0, 0, 0.0, None, None)

        try:
            # Count total entries
            pattern = f"{self.key_prefix}*"
            total_entries = 0
            total_size_bytes = 0
            oldest_entry = None
            newest_entry = None

            async for key in self.redis_client.scan_iter(match=pattern):
                total_entries += 1

                # Get entry to check timestamp and calculate size
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    total_size_bytes += len(cached_data.encode())

                    try:
                        entry_dict = json.loads(cached_data)
                        timestamp = datetime.fromisoformat(entry_dict["timestamp"])

                        if oldest_entry is None or timestamp < oldest_entry:
                            oldest_entry = timestamp
                        if newest_entry is None or timestamp > newest_entry:
                            newest_entry = timestamp
                    except:
                        pass

            # Calculate hit rate
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

            # Convert size to MB
            cache_size_mb = total_size_bytes / (1024 * 1024)

            return CacheStats(
                total_entries=total_entries,
                hit_rate=hit_rate,
                total_cost_saved=self.total_cost_saved,
                total_tokens_saved=self.total_tokens_saved,
                cache_size_mb=cache_size_mb,
                oldest_entry=oldest_entry,
                newest_entry=newest_entry,
            )

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return CacheStats(0, 0.0, 0.0, 0, 0.0, None, None)

    async def _cleanup_if_needed(self) -> None:
        """Clean up cache if it exceeds size limits."""

        try:
            stats = await self.get_stats()

            if stats.cache_size_mb > self.max_cache_size_mb:
                self.logger.info(
                    f"Cache size ({stats.cache_size_mb:.1f}MB) exceeds limit ({self.max_cache_size_mb}MB), cleaning up..."
                )

                # Get all entries with timestamps
                entries_with_timestamps = []
                pattern = f"{self.key_prefix}*"

                async for key in self.redis_client.scan_iter(match=pattern):
                    cached_data = await self.redis_client.get(key)
                    if cached_data:
                        try:
                            entry_dict = json.loads(cached_data)
                            timestamp = datetime.fromisoformat(entry_dict["timestamp"])
                            entries_with_timestamps.append((key, timestamp))
                        except:
                            # Delete corrupted entries
                            await self.redis_client.delete(key)

                # Sort by timestamp (oldest first)
                entries_with_timestamps.sort(key=lambda x: x[1])

                # Delete oldest 25% of entries
                entries_to_delete = len(entries_with_timestamps) // 4
                if entries_to_delete > 0:
                    keys_to_delete = [
                        entry[0]
                        for entry in entries_with_timestamps[:entries_to_delete]
                    ]
                    deleted = await self.redis_client.delete(*keys_to_delete)
                    self.logger.info(f"Cleaned up {deleted} old cache entries")

        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {e}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Redis connection closed")


# Global cache instance
_llm_cache: Optional[LLMCache] = None


async def get_llm_cache() -> LLMCache:
    """Get the global LLM cache instance."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
        await _llm_cache.connect()
    return _llm_cache


async def cached_llm_request(
    prompt: str,
    model: str,
    llm_function,
    token_count_estimate: int = 0,
    cost_estimate: float = 0.0,
    metadata: Dict[str, Any] = None,
    ttl_seconds: int = None,
) -> Tuple[str, bool]:
    """
    Make an LLM request with caching.

    Args:
        prompt: The prompt to send
        model: Model identifier
        llm_function: Async function that makes the actual LLM call
        token_count_estimate: Estimated token count for caching
        cost_estimate: Estimated cost for the request
        metadata: Additional metadata for cache key generation
        ttl_seconds: Cache TTL override

    Returns:
        Tuple of (response, was_cached)
    """

    cache = await get_llm_cache()

    # Try to get from cache first
    cached_entry = await cache.get(prompt, model, metadata)

    if cached_entry:
        return cached_entry.response, True

    # Not in cache, make the request
    try:
        response = await llm_function(prompt)

        # Cache the response
        await cache.set(
            prompt=prompt,
            response=response,
            model=model,
            token_count=token_count_estimate,
            cost_estimate=cost_estimate,
            metadata=metadata,
            ttl_seconds=ttl_seconds,
        )

        return response, False

    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        raise
