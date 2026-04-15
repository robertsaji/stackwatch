"""Retry logic for transient AWS API failures."""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.backoff_factor < 1:
            raise ValueError("backoff_factor must be >= 1")


class Retry:
    """Executes a callable with configurable retry behaviour."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        self._config = config or RetryConfig()
        self._attempt_count = 0

    @property
    def attempt_count(self) -> int:
        return self._attempt_count

    def call(self, fn: Callable[[], T]) -> T:
        """Call *fn*, retrying on retryable exceptions.

        Returns the return value of *fn* on success.
        Raises :class:`RetryError` when all attempts are exhausted.
        """
        cfg = self._config
        delay = cfg.base_delay
        last_exc: Exception | None = None

        for attempt in range(1, cfg.max_attempts + 1):
            self._attempt_count += 1
            try:
                return fn()
            except cfg.retryable_exceptions as exc:  # type: ignore[misc]
                last_exc = exc
                if attempt < cfg.max_attempts:
                    logger.warning(
                        "Attempt %d/%d failed (%s). Retrying in %.1fs.",
                        attempt,
                        cfg.max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= cfg.backoff_factor
                else:
                    logger.error(
                        "All %d attempts failed. Last error: %s",
                        cfg.max_attempts,
                        exc,
                    )

        raise RetryError(
            f"All {cfg.max_attempts} attempts failed"
        ) from last_exc
