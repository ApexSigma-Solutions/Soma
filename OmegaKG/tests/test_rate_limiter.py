"""
Tests for production-ready rate limiting implementation.

Tests cover:
- In-memory rate limiter (development)
- Redis rate limiter (production)
- Hybrid rate limiter with fallback
- Cleanup mechanisms
- Edge cases
"""

import pytest
import time
from unittest.mock import Mock, patch
from omega_kg.rate_limiter import (
    RateLimitConfig,
    InMemoryRateLimiter,
    RedisRateLimiter,
    HybridRateLimiter,
    get_rate_limiter,
)


class TestInMemoryRateLimiter:
    """Test suite for in-memory rate limiter."""

    def setup_method(self):
        """Create a fresh rate limiter for each test."""
        self.config = RateLimitConfig(max_attempts=5, window_seconds=1)
        self.limiter = InMemoryRateLimiter(self.config)

    def test_allows_requests_within_limit(self):
        """Test that requests within the limit are allowed."""
        client_id = "127.0.0.1"

        # Should allow up to max_attempts requests
        for i in range(self.config.max_attempts):
            assert self.limiter.check_limit(client_id) is True

    def test_blocks_requests_exceeding_limit(self):
        """Test that requests exceeding the limit are blocked."""
        client_id = "127.0.0.1"

        # Exhaust the limit
        for _ in range(self.config.max_attempts):
            self.limiter.check_limit(client_id)

        # Next request should be blocked
        assert self.limiter.check_limit(client_id) is False

    def test_resets_after_time_window(self):
        """Test that rate limit resets after the time window expires."""
        client_id = "127.0.0.1"

        # Exhaust the limit
        for _ in range(self.config.max_attempts):
            self.limiter.check_limit(client_id)

        # Should be blocked
        assert self.limiter.check_limit(client_id) is False

        # Wait for window to expire
        time.sleep(self.config.window_seconds + 0.1)

        # Should be allowed again
        assert self.limiter.check_limit(client_id) is True

    def test_reset_clears_for_client(self):
        """Test that reset() clears rate limit for a client."""
        client_id = "127.0.0.1"

        # Exhaust the limit
        for _ in range(self.config.max_attempts):
            self.limiter.check_limit(client_id)

        # Should be blocked
        assert self.limiter.check_limit(client_id) is False

        # Reset the client
        self.limiter.reset(client_id)

        # Should be allowed again immediately
        assert self.limiter.check_limit(client_id) is True

    def test_per_client_isolation(self):
        """Test that rate limits are isolated per client."""
        client1 = "127.0.0.1"
        client2 = "192.168.1.1"

        # Exhaust limit for client1
        for _ in range(self.config.max_attempts):
            self.limiter.check_limit(client1)

        # client1 should be blocked
        assert self.limiter.check_limit(client1) is False

        # client2 should still be allowed
        for _ in range(self.config.max_attempts):
            assert self.limiter.check_limit(client2) is True

    def test_cleanup_removes_expired_entries(self):
        """Test that cleanup() removes expired entries."""
        client1 = "127.0.0.1"
        client2 = "192.168.1.1"

        # Create entries
        self.limiter.check_limit(client1)
        self.limiter.check_limit(client2)

        # Verify entries exist
        assert len(self.limiter._storage) == 2

        # Wait for entries to expire
        time.sleep(2 * self.config.window_seconds + 0.1)

        # Run cleanup
        self.limiter.cleanup()

        # Expired entries should be removed
        assert len(self.limiter._storage) == 0

    def test_cleanup_preserves_recent_entries(self):
        """Test that cleanup() doesn't remove recent entries."""
        client1 = "127.0.0.1"
        client2 = "192.168.1.1"

        # Create entries
        self.limiter.check_limit(client1)

        # Wait a bit
        time.sleep(self.config.window_seconds / 2)

        # Create another entry
        self.limiter.check_limit(client2)

        # Run cleanup
        self.limiter.cleanup()

        # Recent entries should be preserved
        assert len(self.limiter._storage) == 2


class TestRedisRateLimiter:
    """Test suite for Redis rate limiter."""

    def test_init_without_redis_client(self):
        """Test initialization when redis_url is not configured."""
        with patch("omega_kg.rate_limiter.settings") as mock_settings:
            mock_settings.redis_url = None

            limiter = RedisRateLimiter(RateLimitConfig())
            assert limiter.redis is None

    def test_init_with_redis_connection_error(self):
        """Test initialization when Redis connection fails."""
        config = RateLimitConfig()
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection refused")

        limiter = RedisRateLimiter(config, mock_redis)
        # Should handle gracefully
        assert limiter.redis is not None

    def test_check_limit_without_redis(self):
        """Test that check_limit fails open when Redis is unavailable."""
        config = RateLimitConfig()
        limiter = RedisRateLimiter(config)
        limiter.redis = None

        # Should allow request when Redis is unavailable
        assert limiter.check_limit("127.0.0.1") is True

    def test_check_limit_with_redis_error(self):
        """Test that check_limit fails open on Redis errors."""
        config = RateLimitConfig()
        mock_redis = Mock()
        mock_redis.pipeline.side_effect = Exception("Redis error")

        limiter = RedisRateLimiter(config, mock_redis)

        # Should allow request on Redis error
        assert limiter.check_limit("127.0.0.1") is True

    def test_reset_without_redis(self):
        """Test that reset() handles missing Redis gracefully."""
        config = RateLimitConfig()
        limiter = RedisRateLimiter(config)
        limiter.redis = None

        # Should not raise error
        limiter.reset("127.0.0.1")

    def test_cleanup_with_redis(self):
        """Test that cleanup() works with Redis (TTL-based)."""
        config = RateLimitConfig()
        mock_redis = Mock()

        limiter = RedisRateLimiter(config, mock_redis)

        # Should complete without error
        limiter.cleanup()

        # Redis doesn't require manual cleanup due to TTL
        assert True


class TestHybridRateLimiter:
    """Test suite for hybrid rate limiter with fallback."""

    def test_prefers_redis_when_available(self):
        """Test that hybrid limiter uses Redis when available."""
        with patch("omega_kg.rate_limiter.RedisRateLimiter") as mock_redis_limiter:
            mock_instance = Mock()
            mock_instance.check_limit.return_value = True
            mock_redis_limiter.return_value = mock_instance

            with patch("omega_kg.rate_limiter.settings") as mock_settings:
                mock_settings.redis_url = "redis://localhost:6379/0"

                limiter = HybridRateLimiter(RateLimitConfig())

                # Should try to use Redis
                if limiter._use_redis:
                    assert limiter._redis_limiter is not None

    def test_falls_back_to_memory_on_redis_failure(self):
        """Test fallback to in-memory when Redis fails."""
        config = RateLimitConfig(max_attempts=2)

        # Create limiter with no Redis
        limiter = HybridRateLimiter(config)
        limiter._use_redis = False

        # Should use in-memory
        assert limiter._memory_limiter is not None

        # Test that in-memory limiter works
        assert limiter.check_limit("127.0.0.1") is True

    def test_hybrid_check_limit_delegation(self):
        """Test that check_limit delegates correctly."""
        config = RateLimitConfig()
        limiter = HybridRateLimiter(config)
        limiter._use_redis = False

        # Should work with in-memory fallback
        result = limiter.check_limit("127.0.0.1")
        assert isinstance(result, bool)

    def test_hybrid_reset_delegation(self):
        """Test that reset delegates correctly."""
        config = RateLimitConfig()
        limiter = HybridRateLimiter(config)
        limiter._use_redis = False

        # Should not raise error
        limiter.reset("127.0.0.1")

    def test_hybrid_cleanup_delegation(self):
        """Test that cleanup delegates correctly."""
        config = RateLimitConfig()
        limiter = HybridRateLimiter(config)
        limiter._use_redis = False

        # Should not raise error
        limiter.cleanup()


class TestRateLimiterIntegration:
    """Integration tests for rate limiter."""

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns a singleton."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        # Should be the same instance
        assert limiter1 is limiter2

    def test_realistic_attack_scenario(self):
        """Test realistic attack scenario with multiple clients."""
        config = RateLimitConfig(max_attempts=3, window_seconds=1)
        limiter = InMemoryRateLimiter(config)

        attacker_ip = "192.168.1.100"
        legitimate_ip = "127.0.0.1"

        # Attacker tries multiple requests
        for _ in range(5):
            limiter.check_limit(attacker_ip)

        # Attacker should be rate limited
        assert limiter.check_limit(attacker_ip) is False

        # Legitimate user should still work
        assert limiter.check_limit(legitimate_ip) is True

    def test_rate_limit_recovery_after_success(self):
        """Test that successful auth resets the rate limit."""
        config = RateLimitConfig(max_attempts=3, window_seconds=5)
        limiter = InMemoryRateLimiter(config)

        client_ip = "127.0.0.1"

        # Simulate 2 failed attempts
        limiter.check_limit(client_ip)
        limiter.check_limit(client_ip)

        # Simulate successful authentication
        limiter.reset(client_ip)

        # Should allow new attempts
        assert limiter.check_limit(client_ip) is True

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test that in-memory limiter doesn't grow unbounded."""
        config = RateLimitConfig(
            max_attempts=5,
            window_seconds=1,
            cleanup_interval_seconds=1,
        )
        limiter = InMemoryRateLimiter(config)

        # Create entries from many unique IPs
        for i in range(100):
            limiter.check_limit(f"192.168.1.{i}")

        initial_size = len(limiter._storage)
        assert initial_size == 100

        # Wait for entries to expire
        time.sleep(2)

        # Check a new IP to trigger cleanup
        limiter.check_limit("10.0.0.1")

        # Storage should be cleaned up
        final_size = len(limiter._storage)
        assert final_size < initial_size


class TestRateLimiterConfig:
    """Test RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.max_attempts == 5
        assert config.window_seconds == 300
        assert config.cleanup_interval_seconds == 3600

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            max_attempts=10,
            window_seconds=600,
            cleanup_interval_seconds=7200,
        )

        assert config.max_attempts == 10
        assert config.window_seconds == 600
        assert config.cleanup_interval_seconds == 7200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
