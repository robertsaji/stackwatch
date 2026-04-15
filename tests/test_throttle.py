"""Tests for stackwatch.throttle."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from stackwatch.throttle import Throttle, ThrottleConfig, ThrottleError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _throttle(max_calls: int = 3, period: float = 1.0, raise_on_limit: bool = False) -> Throttle:
    return Throttle(ThrottleConfig(max_calls=max_calls, period_seconds=period, raise_on_limit=raise_on_limit))


# ---------------------------------------------------------------------------
# construction guards
# ---------------------------------------------------------------------------

def test_invalid_max_calls_raises() -> None:
    with pytest.raises(ValueError, match="max_calls"):
        Throttle(ThrottleConfig(max_calls=0))


def test_invalid_period_raises() -> None:
    with pytest.raises(ValueError, match="period_seconds"):
        Throttle(ThrottleConfig(max_calls=1, period_seconds=0.0))


# ---------------------------------------------------------------------------
# basic acquire behaviour
# ---------------------------------------------------------------------------

def test_acquire_within_limit_does_not_block() -> None:
    t = _throttle(max_calls=5, period=1.0)
    start = time.monotonic()
    for _ in range(5):
        t.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1, "Should not have blocked"


def test_call_count_increments() -> None:
    t = _throttle(max_calls=10)
    for i in range(4):
        t.acquire()
    assert t.call_count == 4


# ---------------------------------------------------------------------------
# raise_on_limit mode
# ---------------------------------------------------------------------------

def test_raise_on_limit_raises_throttle_error() -> None:
    t = _throttle(max_calls=2, period=60.0, raise_on_limit=True)
    t.acquire()
    t.acquire()
    with pytest.raises(ThrottleError):
        t.acquire()


def test_raise_on_limit_error_message() -> None:
    t = _throttle(max_calls=1, period=30.0, raise_on_limit=True)
    t.acquire()
    with pytest.raises(ThrottleError, match="Rate limit exceeded"):
        t.acquire()


# ---------------------------------------------------------------------------
# window eviction
# ---------------------------------------------------------------------------

def test_old_calls_evicted_after_window() -> None:
    """Calls outside the window should not count toward the limit."""
    t = _throttle(max_calls=3, period=1.0)

    fake_now = [0.0]

    def _monotonic() -> float:
        return fake_now[0]

    with patch("stackwatch.throttle.time.monotonic", side_effect=_monotonic):
        # fill the window at t=0
        for _ in range(3):
            t.acquire()

        # advance time past the window
        fake_now[0] = 1.1
        # eviction should allow a new call without sleeping
        assert t.call_count == 0
        t.acquire()   # should not raise


# ---------------------------------------------------------------------------
# sleep path (non-raise mode)
# ---------------------------------------------------------------------------

def test_acquire_sleeps_when_limit_reached() -> None:
    slept: list[float] = []

    t = _throttle(max_calls=2, period=1.0, raise_on_limit=False)

    call_times = iter([0.0, 0.0, 0.0, 0.0, 1.1, 1.1])

    def _monotonic() -> float:
        return next(call_times)

    with patch("stackwatch.throttle.time.monotonic", side_effect=_monotonic), \
         patch("stackwatch.throttle.time.sleep", side_effect=slept.append):
        t.acquire()  # slot 1
        t.acquire()  # slot 2
        t.acquire()  # should sleep then succeed on retry

    assert slept, "Expected at least one sleep call"
