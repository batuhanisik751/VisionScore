"""In-memory sliding window rate limiter for API key-authenticated requests."""

from __future__ import annotations

import time
from collections import deque


class RateLimiter:
    """Per-key sliding window rate limiter.

    Tracks request timestamps in a ``deque`` per key hash, pruning entries
    older than 60 seconds on each check.
    """

    def __init__(self) -> None:
        self._windows: dict[str, deque[float]] = {}

    def check(self, key: str, limit: int) -> tuple[bool, int, int]:
        """Check whether *key* is under *limit* requests per minute.

        Returns ``(allowed, remaining, retry_after_seconds)``.
        """
        now = time.monotonic()
        cutoff = now - 60.0

        window = self._windows.get(key)
        if window is None:
            window = deque()
            self._windows[key] = window

        # Prune expired entries
        while window and window[0] < cutoff:
            window.popleft()

        remaining = max(0, limit - len(window))

        if len(window) >= limit:
            retry_after = int(window[0] - cutoff) + 1
            return False, 0, retry_after

        window.append(now)
        return True, remaining - 1, 0


# Module-level singleton
_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Return the global rate limiter instance."""
    return _limiter
