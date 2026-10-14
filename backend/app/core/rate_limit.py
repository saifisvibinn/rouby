"""Simple in-memory sliding-window rate limiter (single-process / per-worker)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from app.core.errors import AppError


class RateLimitExceeded(AppError):
    def __init__(self, message: str = "Too many requests") -> None:
        super().__init__("RATE_LIMITED", message, status_code=429)


class SlidingWindowRateLimiter:
    def __init__(self, *, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        window = self._hits[key]
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.max_calls:
            raise RateLimitExceeded("Too many login attempts; try again shortly")
        window.append(now)

    def reset(self) -> None:
        self._hits.clear()


login_rate_limiter = SlidingWindowRateLimiter(max_calls=10, window_seconds=60.0)
