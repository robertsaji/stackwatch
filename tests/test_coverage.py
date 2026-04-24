"""Tests for stackwatch.coverage."""
from __future__ import annotations

from stackwatch.coverage import (
    CoverageReport,
    build_coverage_report,
    render_coverage_text,
)
from stackwatch.drift import DriftResult


def _make_result(stack_name: str, has_drift: bool = False) -> DriftResult:
    return DriftResult(stack_name=stack_name, has_drift=has_drift, drifted_resources=[])


# ---------------------------------------------------------------------------
# build_coverage_report
# ---------------------------------------------------------------------------

def test_build_coverage_empty_all_stacks() -> None:
    report = build_coverage_report([], [])
    assert report.total_stacks == 0
    assert report.monitored_stacks == 0
    assert report.unmonitored_stacks == []


def test_build_coverage_full_coverage() -> None:
    all_stacks = ["alpha", "beta", "gamma"]
    results = [_make_result(n) for n in all_stacks]
    report = build_coverage_report(all_stacks, results)
    assert report.total_stacks == 3
    assert report.monitored_stacks == 3
    assert report.unmonitored_stacks == []
    assert report.is_full_coverage is True


def test_build_coverage_partial_coverage() -> None:
    all_stacks = ["alpha", "beta", "gamma"]
    results = [_make_result("alpha"), _make_result("beta")]
    report = build_coverage_report(all_stacks, results)
    assert report.total_stacks == 3
    assert report.monitored_stacks == 2
    assert "gamma" in report.unmonitored_stacks
    assert report.is_full_coverage is False


def test_coverage_rate_calculation() -> None:
    all_stacks = ["a", "b", "c", "d"]
    results = [_make_result("a"), _make_result("b")]
    report = build_coverage_report(all_stacks, results)
    assert report.coverage_rate == 0.5
    assert report.coverage_pct == 50.0


def test_coverage_rate_zero_total() -> None:
    report = CoverageReport(total_stacks=0, monitored_stacks=0, unmonitored_stacks=[])
    assert report.coverage_rate == 0.0


def test_extra_results_not_in_all_stacks_ignored() -> None:
    """Results for stacks not in all_stack_names should not inflate monitored count."""
    all_stacks = ["alpha"]
    results = [_make_result("alpha"), _make_result("ghost")]
    report = build_coverage_report(all_stacks, results)
    assert report.total_stacks == 1
    assert report.monitored_stacks == 1


# ---------------------------------------------------------------------------
# render_coverage_text
# ---------------------------------------------------------------------------

def test_render_text_full_coverage() -> None:
    report = CoverageReport(total_stacks=2, monitored_stacks=2, unmonitored_stacks=[])
    text = render_coverage_text(report)
    assert "100.0%" in text
    assert "All stacks are monitored" in text


def test_render_text_partial_coverage() -> None:
    report = CoverageReport(
        total_stacks=3,
        monitored_stacks=2,
        unmonitored_stacks=["gamma"],
    )
    text = render_coverage_text(report)
    assert "gamma" in text
    assert "Unmonitored stacks" in text
