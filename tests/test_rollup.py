"""Tests for stackwatch.rollup."""
import pytest
from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.rollup import build_rollup, render_rollup_text, RollupReport


def _make_result(name: str, drifted: bool) -> DriftResult:
    resources = [
        DriftedResource(logical_id="R1", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=[])
    ] if drifted else []
    return DriftResult(stack_name=name, status="DRIFTED" if drifted else "IN_SYNC", resources=resources)


@pytest.fixture
def two_runs():
    run1 = [_make_result("stack-a", True), _make_result("stack-b", False)]
    run2 = [_make_result("stack-a", True), _make_result("stack-b", True)]
    return [run1, run2]


def test_build_rollup_empty():
    report = build_rollup([])
    assert report.total_stacks == 0
    assert report.entries == []


def test_build_rollup_counts(two_runs):
    report = build_rollup(two_runs)
    assert report.total_stacks == 2
    a = next(e for e in report.entries if e.stack_name == "stack-a")
    b = next(e for e in report.entries if e.stack_name == "stack-b")
    assert a.total_checks == 2
    assert a.drifted_checks == 2
    assert b.total_checks == 2
    assert b.drifted_checks == 1


def test_drift_rate(two_runs):
    report = build_rollup(two_runs)
    a = next(e for e in report.entries if e.stack_name == "stack-a")
    assert a.drift_rate == 1.0
    b = next(e for e in report.entries if e.stack_name == "stack-b")
    assert b.drift_rate == 0.5


def test_always_drifted(two_runs):
    report = build_rollup(two_runs)
    assert len(report.always_drifted) == 1
    assert report.always_drifted[0].stack_name == "stack-a"


def test_never_drifted():
    runs = [[_make_result("stack-c", False)], [_make_result("stack-c", False)]]
    report = build_rollup(runs)
    assert len(report.never_drifted) == 1


def test_render_rollup_text_empty():
    text = render_rollup_text(RollupReport())
    assert "No data" in text


def test_render_rollup_text_contains_stack(two_runs):
    report = build_rollup(two_runs)
    text = render_rollup_text(report)
    assert "stack-a" in text
    assert "stack-b" in text
    assert "100%" in text
