"""Tests for DiffNotifier."""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from stackwatch.diff_notifier import DiffNotifier
from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.snapshot import Snapshot


def _make_result(name: str, drifted: bool) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="R", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})]
        if drifted
        else []
    )
    return DriftResult(stack_name=name, drifted_resources=resources, checked_at="2024-01-01T00:00:00")


@pytest.fixture
def notifier():
    return MagicMock()


def test_first_run_notifies_drifted_stacks(notifier):
    results = [_make_result("stack-a", True), _make_result("stack-b", False)]
    current = Snapshot.from_results(results)
    dn = DiffNotifier(notifier=notifier, previous=None)
    dn.notify_changes(results, current)
    notifier.send.assert_called_once()
    assert notifier.send.call_args == call(results[0])


def test_no_notification_when_state_unchanged(notifier):
    results = [_make_result("stack-a", True)]
    snap1 = Snapshot.from_results(results)
    snap2 = Snapshot.from_results(results)
    dn = DiffNotifier(notifier=notifier, previous=snap1)
    dn.notify_changes(results, snap2)
    notifier.send.assert_not_called()


def test_notifies_newly_drifted(notifier):
    old_results = [_make_result("stack-a", False)]
    new_results = [_make_result("stack-a", True)]
    snap1 = Snapshot.from_results(old_results)
    snap2 = Snapshot.from_results(new_results)
    dn = DiffNotifier(notifier=notifier, previous=snap1)
    dn.notify_changes(new_results, snap2)
    notifier.send.assert_called_once()


def test_notifies_newly_resolved(notifier):
    old_results = [_make_result("stack-a", True)]
    new_results = [_make_result("stack-a", False)]
    snap1 = Snapshot.from_results(old_results)
    snap2 = Snapshot.from_results(new_results)
    dn = DiffNotifier(notifier=notifier, previous=snap1)
    dn.notify_changes(new_results, snap2)
    notifier.send.assert_called_once()


def test_render_returns_string(notifier):
    results = [_make_result("stack-a", True)]
    snap1 = Snapshot.from_results([])
    snap2 = Snapshot.from_results(results)
    dn = DiffNotifier(notifier=notifier, previous=snap1)
    report = dn.notify_changes(results, snap2)
    text = dn.render(report)
    assert isinstance(text, str)
    assert "stack-a" in text
