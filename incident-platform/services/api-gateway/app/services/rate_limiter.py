# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Sliding-window rate limiter keyed by client IP."""
import time
from collections import defaultdict


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        now = time.monotonic()
        cutoff = now - self.window
        timestamps = self._hits[key]
        self._hits[key] = timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= self.max_requests:
            retry_after = int(timestamps[0] - cutoff) + 1
            return False, 0, retry_after
        timestamps.append(now)
        return True, self.max_requests - len(timestamps), 0
