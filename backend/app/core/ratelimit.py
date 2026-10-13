"""A small in-process, per-client rate limiter.

State lives in memory, so limits are per server instance and reset on restart. That is
enough to slow down abuse of login and public booking in a single-instance demo.
"""

import math
import threading
import time
from collections import deque

from fastapi import Request

from app.core.errors import AppError

_MAX_TRACKED_KEYS = 10_000


class RateLimiter:
    """Sliding-window counter keyed by an arbitrary string."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float, now: float) -> int | None:
        """Record a hit. Return None if allowed, else the seconds until a retry can succeed."""
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._purge(now - window_seconds)
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(hits[0] + window_seconds - now))
            hits.append(now)
            return None

    def _purge(self, cutoff: float) -> None:
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]


def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int = 60) -> None:
    """Raise 429 when the calling client has made too many requests in this scope."""
    limiter: RateLimiter = request.app.state.rate_limiter
    client = request.client.host if request.client else "unknown"
    retry_after = limiter.check(f"{scope}:{client}", limit, window_seconds, time.monotonic())
    if retry_after is not None:
        raise AppError(
            429,
            "rate_limited",
            "Too many attempts. Please try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
