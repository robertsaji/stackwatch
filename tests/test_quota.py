"""Tests for stackwatch.quota."""
from __future__ import annotations
import time
import pytest
from stackwatch.quota import QuotaConfig, QuotaError, QuotaTracker


@pytest.fixture
def config() -> QuotaConfig:
    return QuotaConfig(max_detections_per_minute=3, max_concurrent_stacks=5)


@pytest.fixture
def tracker(config: QuotaConfig) -> QuotaTracker:
    return QuotaTracker(config=config)


def test_invalid_max_detections_raises() -> None:
    with pytest.raises(QuotaError):
        QuotaConfig(max_detections_per_minute=0)


def test_invalid_max_concurrent_raises() -> None:
    with pytest.raises(QuotaError):
        QuotaConfig(max_concurrent_stacks=0)


def test_can_detect_initially(tracker: QuotaTracker) -> None:
    assert tracker.can_detect() is True


def test_usage_count_starts_at_zero(tracker: QuotaTracker) -> None:
    assert tracker.usage_count() == 0


def test_remaining_starts_at_max(tracker: QuotaTracker) -> None:
    assert tracker.remaining() == 3


def test_record_increments_usage(tracker: QuotaTracker) -> None:
    tracker.record("stack-a")
    assert tracker.usage_count() == 1
    assert tracker.remaining() == 2


def test_record_tracks_stack_names(tracker: QuotaTracker) -> None:
    tracker.record("stack-a")
    tracker.record("stack-b")
    assert "stack-a" in tracker.stacks_detected()
    assert "stack-b" in tracker.stacks_detected()


def test_quota_exceeded_raises(tracker: QuotaTracker) -> None:
    tracker.record("s1")
    tracker.record("s2")
    tracker.record("s3")
    with pytest.raises(QuotaError, match="quota exceeded"):
        tracker.record("s4")


def test_old_entries_pruned(tracker: QuotaTracker) -> None:
    tracker.record("old-stack")
    # Backdate the entry
    tracker._history[0].detected_at = time.time() - 61
    assert tracker.usage_count() == 0
    assert tracker.can_detect() is True
