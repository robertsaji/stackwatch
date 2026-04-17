"""Tests for stackwatch.retry."""
import pytest
from unittest.mock import MagicMock, patch

from stackwatch.retry import Retry, RetryConfig, RetryError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def default_retry() -> Retry:
    cfg = RetryConfig(max_attempts=3, base_delay=0.0, backoff_factor=1.0)
    return Retry(cfg)


# ---------------------------------------------------------------------------
# RetryConfig validation
# ---------------------------------------------------------------------------

def test_invalid_max_attempts_raises() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryConfig(max_attempts=0)


def test_negative_base_delay_raises() -> None:
    with pytest.raises(ValueError, match="base_delay"):
        RetryConfig(base_delay=-1.0)


def test_backoff_factor_below_one_raises() -> None:
    with pytest.raises(ValueError, match="backoff_factor"):
        RetryConfig(backoff_factor=0.5)


# ---------------------------------------------------------------------------
# Retry.call — success paths
# ---------------------------------------------------------------------------

def test_call_succeeds_on_first_attempt(default_retry: Retry) -> None:
    fn = MagicMock(return_value=42)
    result = default_retry.call(fn)
    assert result == 42
    assert default_retry.attempt_count == 1
    fn.assert_called_once()


def test_call_succeeds_after_transient_failure(default_retry: Retry) -> None:
    fn = MagicMock(side_effect=[RuntimeError("boom"), RuntimeError("boom"), "ok"])
    result = default_retry.call(fn)
    assert result == "ok"
    assert default_retry.attempt_count == 3


# ---------------------------------------------------------------------------
# Retry.call — failure paths
# ---------------------------------------------------------------------------

def test_call_raises_retry_error_when_exhausted(default_retry: Retry) -> None:
    fn = MagicMock(side_effect=RuntimeError("always fails"))
    with pytest.raises(RetryError):
        default_retry.call(fn)
    assert default_retry.attempt_count == 3


def test_retry_error_chains_original_exception(default_retry: Retry) -> None:
    original = ValueError("root cause")
    fn = MagicMock(side_effect=original)
    with pytest.raises(RetryError) as exc_info:
        default_retry.call(fn)
    assert exc_info.value.__cause__ is original


# ---------------------------------------------------------------------------
# Retryable exceptions filter
# ---------------------------------------------------------------------------

def test_non_retryable_exception_propagates_immediately() -> None:
    cfg = RetryConfig(
        max_attempts=3,
        base_delay=0.0,
        retryable_exceptions=(IOError,),
    )
    retry = Retry(cfg)
    fn = MagicMock(side_effect=ValueError("not retryable"))
    with pytest.raises(ValueError, match="not retryable"):
        retry.call(fn)
    # Should have stopped after the first attempt without retrying.
    assert retry.attempt_count == 1


def test_retryable_exception_is_retried() -> None:
    cfg = RetryConfig(
        max_attempts=3,
        base_delay=0.0,
        retryable_exceptions=(IOError,),
    )
    retry = Retry(cfg)
    fn = MagicMock(side_effect=[IOError("transient"), IOError("transient"), "done"])
    result = retry.call(fn)
    assert result == "done"
    assert retry.attempt_count == 3
