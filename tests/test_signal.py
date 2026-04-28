"""Tests for stackwatch.signal."""
from __future__ import annotations

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.signal import (
    SignalConfig,
    StackSignal,
    SignalReport,
    build_signal_report,
    render_signal_text,
)


def _make_resource(status: str = "MODIFIED") -> DriftedResource:
    return DriftedResource(
        logical_id="Res",
        resource_type="AWS::S3::Bucket",
        drift_status=status,
        expected_properties="{}",
        actual_properties="{}",
    )


def _make_result(name: str, drifted: bool = True, n_resources: int = 2) -> DriftResult:
    if drifted:
        resources = [_make_resource() for _ in range(n_resources)]
    else:
        resources = [_make_resource(status="NOT_CHECKED") for _ in range(n_resources)]
    return DriftResult(
        stack_name=name,
        drift_status="DRIFTED" if drifted else "IN_SYNC",
        resources=resources,
    )


# ---------------------------------------------------------------------------
# SignalConfig validation
# ---------------------------------------------------------------------------

def test_invalid_drift_weight_raises():
    with pytest.raises(ValueError, match="drift_weight"):
        SignalConfig(drift_weight=-1.0)


def test_invalid_severity_weight_raises():
    with pytest.raises(ValueError, match="severity_weight"):
        SignalConfig(severity_weight=-0.1)


def test_invalid_recurrence_weight_raises():
    with pytest.raises(ValueError, match="recurrence_weight"):
        SignalConfig(recurrence_weight=-5)


# ---------------------------------------------------------------------------
# build_signal_report
# ---------------------------------------------------------------------------

def test_build_signal_report_empty():
    report = build_signal_report([])
    assert report.signals == []


def test_in_sync_result_has_zero_score():
    result = _make_result("stack-a", drifted=False)
    report = build_signal_report([result])
    assert len(report.signals) == 1
    assert report.signals[0].score == 0.0
    assert report.signals[0].label == "low"


def test_drifted_result_has_positive_score():
    result = _make_result("stack-b", drifted=True)
    report = build_signal_report([result])
    assert report.signals[0].score > 0.0


def test_recurrence_increases_score():
    result = _make_result("stack-c", drifted=True)
    report_no_rec = build_signal_report([result], recurrence_map={})
    report_with_rec = build_signal_report([result], recurrence_map={"stack-c": 5})
    assert report_with_rec.signals[0].score > report_no_rec.signals[0].score


def test_top_returns_sorted_by_score():
    results = [
        _make_result("a", drifted=False),
        _make_result("b", drifted=True, n_resources=4),
        _make_result("c", drifted=True, n_resources=1),
    ]
    report = build_signal_report(results)
    top = report.top(2)
    assert len(top) == 2
    assert top[0].score >= top[1].score


def test_critical_property_filters_correctly():
    # Force a critical score by using high recurrence
    result = _make_result("x", drifted=True, n_resources=5)
    report = build_signal_report([result], recurrence_map={"x": 5})
    for sig in report.critical:
        assert sig.label == "critical"


# ---------------------------------------------------------------------------
# render_signal_text
# ---------------------------------------------------------------------------

def test_render_signal_text_contains_stack_name():
    result = _make_result("my-stack", drifted=True)
    report = build_signal_report([result])
    text = render_signal_text(report)
    assert "my-stack" in text


def test_render_signal_text_empty():
    report = build_signal_report([])
    text = render_signal_text(report)
    assert "no stacks" in text
