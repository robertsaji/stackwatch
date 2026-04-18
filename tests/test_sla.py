"""Tests for stackwatch.sla."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from stackwatch.sla import SLAConfig, SLATracker, SLAError


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "sla.json"


@pytest.fixture
def tracker(store_path: Path) -> SLATracker:
    return SLATracker(path=store_path, config=SLAConfig(max_drift_hours=24.0))


def test_invalid_max_hours_raises():
    with pytest.raises(SLAError):
        SLAConfig(max_drift_hours=0)


def test_invalid_threshold_raises():
    with pytest.raises(SLAError):
        SLAConfig(warning_threshold=1.5)


def test_no_record_returns_none(tracker):
    assert tracker.status("my-stack") is None


def test_record_drift_persists(store_path):
    t1 = SLATracker(path=store_path)
    t1.record_drift("stack-a")
    t2 = SLATracker(path=store_path)
    assert t2.status("stack-a") is not None


def test_record_drift_idempotent(tracker):
    first_time = datetime(2024, 1, 1, 0, 0, 0)
    tracker.record_drift("stack-a", at=first_time)
    tracker.record_drift("stack-a", at=datetime(2024, 1, 2, 0, 0, 0))
    s = tracker.status("stack-a")
    assert s.first_drifted_at == first_time


def test_status_not_breached_within_window(tracker):
    start = datetime(2024, 1, 1, 0, 0, 0)
    tracker.record_drift("stack-a", at=start)
    s = tracker.status("stack-a", now=start + timedelta(hours=10))
    assert not s.breached


def test_status_breached_after_deadline(tracker):
    start = datetime(2024, 1, 1, 0, 0, 0)
    tracker.record_drift("stack-a", at=start)
    s = tracker.status("stack-a", now=start + timedelta(hours=25))
    assert s.breached


def test_warning_before_breach(tracker):
    start = datetime(2024, 1, 1, 0, 0, 0)
    tracker.record_drift("stack-a", at=start)
    s = tracker.status("stack-a", now=start + timedelta(hours=20))
    assert s.warning(tracker.config)
    assert not s.breached


def test_clear_removes_record(tracker):
    tracker.record_drift("stack-a")
    tracker.clear("stack-a")
    assert tracker.status("stack-a") is None


def test_all_statuses_returns_all(tracker):
    tracker.record_drift("stack-a")
    tracker.record_drift("stack-b")
    statuses = tracker.all_statuses()
    names = {s.stack_name for s in statuses}
    assert names == {"stack-a", "stack-b"}
