"""Tests for stackwatch.recheck."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.recheck import (
    RecheckConfig,
    RecheckReport,
    build_recheck_targets,
    render_recheck_text,
    run_recheck,
)
from stackwatch.snapshot import Snapshot


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_result(stack_name: str, drifted: bool) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="Res", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})]
        if drifted
        else []
    )
    return DriftResult(stack_name=stack_name, drifted=drifted, resources=resources)


def _make_snapshot(drifted_names, in_sync_names) -> Snapshot:
    snap = MagicMock(spec=Snapshot)
    all_names = list(drifted_names) + list(in_sync_names)
    snap.stack_names = all_names
    snap.drifted = list(drifted_names)
    return snap


# ---------------------------------------------------------------------------
# RecheckConfig validation
# ---------------------------------------------------------------------------

def test_invalid_max_stacks_raises():
    with pytest.raises(ValueError, match="max_stacks"):
        RecheckConfig(max_stacks=0)


def test_valid_config_defaults():
    cfg = RecheckConfig()
    assert cfg.only_drifted is True
    assert cfg.max_stacks is None


# ---------------------------------------------------------------------------
# build_recheck_targets
# ---------------------------------------------------------------------------

def test_only_drifted_returns_drifted_stacks():
    snap = _make_snapshot(["stack-a", "stack-b"], ["stack-c"])
    cfg = RecheckConfig(only_drifted=True)
    targets = build_recheck_targets(snap, cfg)
    assert targets == ["stack-a", "stack-b"]


def test_all_stacks_when_only_drifted_false():
    snap = _make_snapshot(["stack-a"], ["stack-b", "stack-c"])
    cfg = RecheckConfig(only_drifted=False)
    targets = build_recheck_targets(snap, cfg)
    assert set(targets) == {"stack-a", "stack-b", "stack-c"}


def test_max_stacks_caps_targets():
    snap = _make_snapshot(["a", "b", "c"], [])
    cfg = RecheckConfig(only_drifted=True, max_stacks=2)
    targets = build_recheck_targets(snap, cfg)
    assert len(targets) == 2


# ---------------------------------------------------------------------------
# run_recheck
# ---------------------------------------------------------------------------

def test_run_recheck_calls_detector_for_each_target():
    snap = _make_snapshot(["stack-x"], ["stack-y"])
    detector = MagicMock()
    detector.detect.side_effect = lambda name: _make_result(name, drifted=True)

    report = run_recheck(snap, detector)

    detector.detect.assert_called_once_with("stack-x")
    assert report.total_rechecked == 1
    assert report.still_drifted == 1
    assert report.resolved == 0
    assert "stack-y" in report.skipped


def test_run_recheck_resolved_stack():
    snap = _make_snapshot(["stack-x"], [])
    detector = MagicMock()
    detector.detect.return_value = _make_result("stack-x", drifted=False)

    report = run_recheck(snap, detector)

    assert report.resolved == 1
    assert report.still_drifted == 0


def test_run_recheck_uses_default_config_when_none():
    snap = _make_snapshot(["s1", "s2"], ["s3"])
    detector = MagicMock()
    detector.detect.side_effect = lambda name: _make_result(name, drifted=True)

    report = run_recheck(snap, detector, cfg=None)

    assert report.total_rechecked == 2


# ---------------------------------------------------------------------------
# render_recheck_text
# ---------------------------------------------------------------------------

def test_render_text_contains_summary():
    report = RecheckReport(
        rechecked=[_make_result("stack-a", True), _make_result("stack-b", False)],
        skipped=["stack-c"],
    )
    text = render_recheck_text(report)
    assert "2 stack(s) rechecked" in text
    assert "1 still drifted" in text
    assert "1 resolved" in text
    assert "stack-a" in text
    assert "stack-b" in text
    assert "stack-c" in text


def test_render_text_no_skipped():
    report = RecheckReport(rechecked=[_make_result("s", False)], skipped=[])
    text = render_recheck_text(report)
    assert "Skipped" not in text
