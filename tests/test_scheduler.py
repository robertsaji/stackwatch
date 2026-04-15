"""Tests for stackwatch.scheduler."""

import pytest
from unittest.mock import MagicMock, patch

from stackwatch.scheduler import DriftScheduler, SchedulerError


@pytest.fixture()
def mock_task():
    return MagicMock()


def test_invalid_interval_raises():
    with pytest.raises(ValueError, match="positive integer"):
        DriftScheduler(interval_seconds=0, task=lambda: None)


def test_negative_interval_raises():
    with pytest.raises(ValueError):
        DriftScheduler(interval_seconds=-5, task=lambda: None)


def test_runs_task_once_when_max_runs_1(mock_task):
    with patch("stackwatch.scheduler.time.sleep"):
        scheduler = DriftScheduler(interval_seconds=60, task=mock_task, max_runs=1)
        scheduler.start()

    mock_task.assert_called_once()
    assert scheduler.run_count == 1


def test_runs_task_multiple_times(mock_task):
    with patch("stackwatch.scheduler.time.sleep"):
        scheduler = DriftScheduler(interval_seconds=60, task=mock_task, max_runs=3)
        scheduler.start()

    assert mock_task.call_count == 3
    assert scheduler.run_count == 3


def test_task_exception_does_not_stop_scheduler(mock_task):
    mock_task.side_effect = RuntimeError("boom")
    with patch("stackwatch.scheduler.time.sleep"):
        scheduler = DriftScheduler(interval_seconds=60, task=mock_task, max_runs=2)
        scheduler.start()  # should not raise

    assert scheduler.run_count == 2


def test_sleep_called_between_runs(mock_task):
    with patch("stackwatch.scheduler.time.sleep") as mock_sleep:
        scheduler = DriftScheduler(interval_seconds=30, task=mock_task, max_runs=2)
        scheduler.start()

    # sleep is called once between two runs (not after the last)
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_with(30)


def test_stop_sets_running_false(mock_task):
    scheduler = DriftScheduler(interval_seconds=60, task=mock_task, max_runs=1)
    with patch("stackwatch.scheduler.time.sleep"):
        scheduler.start()
    scheduler.stop()
    assert not scheduler._running
