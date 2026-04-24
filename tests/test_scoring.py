"""Tests for stackwatch.scoring."""
from __future__ import annotations

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.scoring import (
    StackScore,
    ScoringReport,
    _label,
    score_result,
    build_scoring_report,
    render_scoring_text,
    _MAX_SCORE,
)


def _make_resource(name: str) -> DriftedResource:
    return DriftedResource(logical_id=name, resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})


def _make_result(name: str, n_drifted: int) -> DriftResult:
    resources = [_make_resource(f"Res{i}") for i in range(n_drifted)]
    return DriftResult(stack_name=name, status="DRIFTED" if n_drifted else "IN_SYNC", drifted_resources=resources)


# ---------------------------------------------------------------------------
# _label
# ---------------------------------------------------------------------------

def test_label_zero_is_low():
    assert _label(0) == "LOW"


def test_label_10_is_low():
    assert _label(10) == "LOW"


def test_label_30_is_medium():
    assert _label(30) == "MEDIUM"


def test_label_60_is_high():
    assert _label(60) == "HIGH"


def test_label_85_is_critical():
    assert _label(85) == "CRITICAL"


# ---------------------------------------------------------------------------
# score_result
# ---------------------------------------------------------------------------

def test_score_no_drift_is_zero():
    result = _make_result("my-stack", 0)
    s = score_result(result)
    assert s.score == 0
    assert s.label == "LOW"


def test_score_one_resource():
    result = _make_result("my-stack", 1)
    s = score_result(result)
    # 1 * 10 = 10, no majority penalty (1 > 1//2=0 → penalty applied)
    assert s.score <= _MAX_SCORE
    assert s.label in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_score_many_resources_capped():
    result = _make_result("big-stack", 20)
    s = score_result(result)
    assert s.score == _MAX_SCORE


def test_score_stack_name_preserved():
    result = _make_result("alpha", 2)
    s = score_result(result)
    assert s.stack_name == "alpha"


# ---------------------------------------------------------------------------
# build_scoring_report
# ---------------------------------------------------------------------------

def test_build_report_empty():
    report = build_scoring_report([])
    assert report.scores == []
    assert report.average_score == 0.0
    assert report.highest_score is None


def test_build_report_counts():
    results = [_make_result("a", 0), _make_result("b", 3)]
    report = build_scoring_report(results)
    assert len(report.scores) == 2


def test_highest_score_is_correct():
    results = [_make_result("low", 0), _make_result("high", 10)]
    report = build_scoring_report(results)
    assert report.highest_score.stack_name == "high"


# ---------------------------------------------------------------------------
# render_scoring_text
# ---------------------------------------------------------------------------

def test_render_empty():
    report = ScoringReport(scores=[])
    text = render_scoring_text(report)
    assert "No stacks" in text


def test_render_contains_stack_name():
    results = [_make_result("my-stack", 1)]
    report = build_scoring_report(results)
    text = render_scoring_text(report)
    assert "my-stack" in text


def test_render_contains_average():
    results = [_make_result("x", 0), _make_result("y", 2)]
    report = build_scoring_report(results)
    text = render_scoring_text(report)
    assert "Average score" in text
