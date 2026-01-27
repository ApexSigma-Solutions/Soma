"""
Production-ready rate limiting module using Redis for distributed systems.

Supports both Redis-backed and in-memory fallback modes.
Provides scalable, persistent rate limiting across multiple server processes.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from omega_kg.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_attempts: int = 5
    window_seconds: int = 300  # 5 minutes
    cleanup_interval_seconds: int = 3600  # 1 hour


class RateLimiter(ABC):
    """Abstract base class for rate limiting implementations."""

    @abstractmethod
    def check_limit(self, client_id: str) -> bool:
        """
        Check if a request should be allowed.

        Args:
            client_id: Unique identifier for the client (e.g., IP address)

        Returns:
            bool: True if request is allowed, False if rate limited
        """
        pass

    @abstractmethod
    def reset(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up expired entries."""
        pass


class InMemoryRateLimiter(RateLimiter):
    """
    Simple in-memory rate limiter for development/testing.

    WARNING: Not suitable for production with multiple processes.
    Use RedisRateLimiter for production deployments.
    """

    def __init__(self, config: RateLimitConfig):
        """Initialize in-memory rate limiter."""
        self.config = config
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._last_cleanup = time.time()

    def check_limit(self, client_id: str) -> bool:
        """Check rate limit using in-memory storage."""
        current_time = time.time()

        # Periodic cleanup to prevent unbounded memory growth
        if current_time - self._last_cleanup > self.config.cleanup_interval_seconds:
            self.cleanup()
            self._last_cleanup = current_time

        if client_id not in self._storage:
            self._storage[client_id] = {
                "count": 1,
                "first_attempt": current_time,
                "last_attempt": current_time,
            }
            return True

        client_data = self._storage[client_id]

        # Reset if outside time window
        if current_time - client_data["first_attempt"] > self.config.window_seconds:
            self._storage[client_id] = {
                "count": 1,
                "first_attempt": current_time,
                "last_attempt": current_time,
            }
            return True

        # Check if rate limit exceeded
        if client_data["count"] >= self.config.max_attempts:
            client_data["last_attempt"] = current_time
            return False

        # Increment attempt counter
        client_data["count"] += 1
        client_data["last_attempt"] = current_time
        return True

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client after successful authentication."""
        if client_id in self._storage:
            del self._storage[client_id]

    def cleanup(self) -> None:
        """Remove expired entries from storage."""
        current_time = time.time()
        expired_clients = []

        for client_id, data in self._storage.items():
            # Remove entries that haven't been accessed in 2x the window
            if current_time - data["last_attempt"] > 2 * self.config.window_seconds:
                expired_clients.append(client_id)

        for client_id in expired_clients:
            del self._storage[client_id]

        if expired_clients:
            logger.debug(
                "Rate limiter cleanup: removed %d expired entries",
                len(expired_clients),
            )


class RedisRateLimiter(RateLimiter):
    """
    Production-ready rate limiter using Redis.

    Features:
    - Distributed across multiple processes and servers
    - Persistent storage survives server restarts
    - Automatic expiration using Redis TTL
    - Memory efficient with bounded key count
    """

    def __init__(self, config: RateLimitConfig, redis_client: Optional[Any] = None):
        """
        Initialize Redis rate limiter.

        Args:
            config: Rate limiting configuration
            redis_client: Redis client instance (will create if not provided)
        """
        self.config = config
        self.redis = redis_client
        self._key_prefix = "rate_limit:api_key:"

        if self.redis is None:
            self._initialize_redis()

    def _initialize_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis

            redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
            self.redis = redis.from_url(redis_url, decode_responses=True)

            # Test connection
            self.redis.ping()
            logger.info("Redis connection established for rate limiting")

        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            self.redis = None
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", str(e))
            self.redis = None

    def check_limit(self, client_id: str) -> bool:
        """Check rate limit using Redis."""
        if not self.redis:
            logger.warning("Redis unavailable, rate limiting disabled")
            return True

        try:
            key = f"{self._key_prefix}{client_id}"
            current_time = int(time.time())

            # Atomic operation: check and increment with expiration
            pipe = self.redis.pipeline()
            pipe.get(key)
            pipe.incr(key)
            pipe.expire(key, self.config.window_seconds)

            results = pipe.execute()

            # Get current count
            current_count = int(results[1])

            # Set initial timestamp on first request in window
            if current_count == 1:
                self.redis.set(
                    f"{key}:started", current_time, ex=self.config.window_seconds
                )

            # Check if over limit
            if current_count > self.config.max_attempts:
                logger.warning(
                    "Rate limit exceeded for client %s (attempts: %d/%d)",
                    client_id,
                    current_count,
                    self.config.max_attempts,
                )
                return False

            return True

        except Exception as e:
            logger.error("Rate limiting check failed: %s", str(e))
            # Fail open: allow request if Redis is having issues
            return True

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client after successful authentication."""
        if not self.redis:
            return

        try:
            key = f"{self._key_prefix}{client_id}"
            self.redis.delete(key, f"{key}:started")
            logger.debug("Rate limit reset for client %s", client_id)
        except Exception as e:
            logger.error("Failed to reset rate limit: %s", str(e))

    def cleanup(self) -> None:
        """
        Clean up expired entries.
        Note: Redis handles this automatically with TTL, but this
        method is provided for consistency with the interface.
        """
        # Redis TTL handles cleanup automatically, nothing to do here
        logger.debug("Redis rate limiter cleanup (TTL-based, no action needed)")


class HybridRateLimiter(RateLimiter):
    """
    Hybrid rate limiter that falls back from Redis to in-memory.

    Tries Redis first for distributed deployments,
    falls back to in-memory for development/testing.
    """

    def __init__(self, config: RateLimitConfig):
        """Initialize hybrid rate limiter."""
        self.config = config
        self._redis_limiter: Optional[RedisRateLimiter] = None
        self._memory_limiter = InMemoryRateLimiter(config)
        self._use_redis = False

        # Try to initialize Redis
        try:
            import redis

            redis_url = getattr(settings, "redis_url", None)
            if redis_url:
                redis_client = redis.from_url(redis_url, decode_responses=True)
                redis_client.ping()
                self._redis_limiter = RedisRateLimiter(config, redis_client)
                self._use_redis = True
                logger.info("Using Redis for rate limiting")
            else:
                logger.info("No Redis URL configured, using in-memory rate limiting")
        except Exception as e:
            logger.warning(
                "Redis rate limiting unavailable, falling back to in-memory: %s",
                str(e),
            )

    def check_limit(self, client_id: str) -> bool:
        """Check rate limit with automatic fallback."""
        if self._use_redis and self._redis_limiter:
            try:
                return self._redis_limiter.check_limit(client_id)
            except Exception as e:
                logger.error(
                    "Redis rate limiting failed, falling back to memory: %s", str(e)
                )
                self._use_redis = False

        # Fall back to in-memory
        return self._memory_limiter.check_limit(client_id)

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client."""
        if self._use_redis and self._redis_limiter:
            try:
                self._redis_limiter.reset(client_id)
                return
            except Exception as e:
                logger.error("Redis reset failed, using memory fallback: %s", str(e))

        self._memory_limiter.reset(client_id)

    def cleanup(self) -> None:
        """Clean up expired entries."""
        if self._use_redis and self._redis_limiter:
            try:
                self._redis_limiter.cleanup()
                return
            except Exception as e:
                logger.error("Redis cleanup failed: %s", str(e))

        self._memory_limiter.cleanup()


# Global rate limiter instance
_rate_limiter: Optional[HybridRateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter

    if _rate_limiter is None:
        config = RateLimitConfig(max_attempts=5, window_seconds=300)
        _rate_limiter = HybridRateLimiter(config)

    return _rate_limiter

    return _rate_limiter
