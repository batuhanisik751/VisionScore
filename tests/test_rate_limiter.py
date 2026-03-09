"""Tests for the in-memory sliding window rate limiter."""

from __future__ import annotations

import time
from unittest.mock import patch

from visionscore.api.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_allows_requests_under_limit(self):
        limiter = RateLimiter()
        for _ in range(5):
            allowed, remaining, _ = limiter.check("key1", limit=10)
            assert allowed is True
        assert remaining >= 0

    def test_blocks_requests_over_limit(self):
        limiter = RateLimiter()
        for _ in range(5):
            limiter.check("key1", limit=5)

        allowed, remaining, retry_after = limiter.check("key1", limit=5)
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_window_slides_after_expiry(self):
        limiter = RateLimiter()

        # Fill window
        for _ in range(3):
            limiter.check("key1", limit=3)

        # Blocked now
        allowed, _, _ = limiter.check("key1", limit=3)
        assert allowed is False

        # Fast-forward past the 60s window by manipulating timestamps
        window = limiter._windows["key1"]
        old_time = time.monotonic() - 61
        window.clear()
        window.append(old_time)
        window.append(old_time)
        window.append(old_time)

        # Should be allowed now (old entries get pruned)
        allowed, _, _ = limiter.check("key1", limit=3)
        assert allowed is True

    def test_different_keys_independent(self):
        limiter = RateLimiter()

        # Fill key1 to limit
        for _ in range(3):
            limiter.check("key1", limit=3)

        # key1 blocked
        allowed, _, _ = limiter.check("key1", limit=3)
        assert allowed is False

        # key2 still allowed
        allowed, _, _ = limiter.check("key2", limit=3)
        assert allowed is True

    def test_remaining_decrements(self):
        limiter = RateLimiter()
        _, remaining1, _ = limiter.check("key1", limit=5)
        _, remaining2, _ = limiter.check("key1", limit=5)
        assert remaining1 == 4
        assert remaining2 == 3

    def test_retry_after_is_positive(self):
        limiter = RateLimiter()
        for _ in range(2):
            limiter.check("key1", limit=2)

        _, _, retry_after = limiter.check("key1", limit=2)
        assert retry_after >= 1
