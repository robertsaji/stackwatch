"""Rate limiting / throttle guard for AWS API calls."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Deque


class ThrottleError(Exception):
    """Raised when the caller exceeds the allowed request rate."""


@dataclass
class ThrottleConfig:
    """Configuration for the token-bucket throttle."""

    max_calls: int = 10          # maximum calls allowed in the window
    period_seconds: float = 1.0  # rolling window size in seconds
    raise_on_limit: bool = False  # if True raise instead of sleeping


class Throttle:
    """Thread-safe sliding-window rate limiter.

    Usage::

        throttle = Throttle(ThrottleConfig(max_calls=5, period_seconds=1.0))
        for stack in stacks:
            throttle.acquire()   # blocks until a slot is available
            client.describe_stack_drift_detection_status(...)
    """

    def __init__(self, config: ThrottleConfig) -> None:
        if config.max_calls < 1:
            raise ValueError("max_calls must be >= 1")
        if config.period_seconds <= 0:
            raise ValueError("period_seconds must be > 0")
        self._config = config
        self._timestamps: Deque[float] = deque()
        self._lock = Lock()

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    @property
    def call_count(self) -> int:
        """Number of calls recorded in the current window."""
        with self._lock:
            self._evict(time.monotonic())
            return len(self._timestamps)

    def acquire(self) -> None:
        """Block (or raise) until a call slot is available."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._evict(now)
                if len(self._timestamps) < self._config.max_calls:
                    self._timestamps.append(now)
                    return
                # oldest call determines how long we must wait
                wait = self._config.period_seconds - (now - self._timestamps[0])

            if self._config.raise_on_limit:
                raise ThrottleError(
                    f"Rate limit exceeded: {self._config.max_calls} calls "
                    f"per {self._config.period_seconds}s"
                )
            if wait > 0:
                time.sleep(wait)

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _evict(self, now: float) -> None:
        """Remove timestamps outside the current window (lock must be held)."""
        cutoff = now - self._config.period_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()
