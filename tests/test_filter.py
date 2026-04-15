"""Tests for stackwatch.filter module."""
import pytest

from stackwatch.drift import DriftResult
from stackwatch.filter import FilterConfig, StackFilter


def _make_result(stack_name: str, drift_status: str = "IN_SYNC") -> DriftResult:
    return DriftResult(
        stack_name=stack_name,
        drift_status=drift_status,
        drifted_resources=[],
    )


@pytest.fixture()
def results():
    return [
        _make_result("prod-api", "DRIFTED"),
        _make_result("prod-db", "IN_SYNC"),
        _make_result("staging-api", "DRIFTED"),
        _make_result("staging-db", "IN_SYNC"),
    ]


def test_no_filter_returns_all(results):
    sf = StackFilter()
    assert sf.apply(results) == results


def test_include_pattern_filters(results):
    cfg = FilterConfig(include_patterns=["prod-*"])
    sf = StackFilter(cfg)
    names = [r.stack_name for r in sf.apply(results)]
    assert names == ["prod-api", "prod-db"]


def test_exclude_pattern_filters(results):
    cfg = FilterConfig(exclude_patterns=["*-db"])
    sf = StackFilter(cfg)
    names = [r.stack_name for r in sf.apply(results)]
    assert names == ["prod-api", "staging-api"]


def test_include_and_exclude_combined(results):
    cfg = FilterConfig(include_patterns=["prod-*"], exclude_patterns=["prod-db"])
    sf = StackFilter(cfg)
    names = [r.stack_name for r in sf.apply(results)]
    assert names == ["prod-api"]


def test_status_filter_drifted_only(results):
    cfg = FilterConfig(statuses=["DRIFTED"])
    sf = StackFilter(cfg)
    statuses = {r.drift_status for r in sf.apply(results)}
    assert statuses == {"DRIFTED"}


def test_status_filter_in_sync_only(results):
    cfg = FilterConfig(statuses=["IN_SYNC"])
    sf = StackFilter(cfg)
    statuses = {r.drift_status for r in sf.apply(results)}
    assert statuses == {"IN_SYNC"}


def test_empty_results_returns_empty():
    sf = StackFilter(FilterConfig(include_patterns=["prod-*"]))
    assert sf.apply([]) == []


def test_no_match_returns_empty(results):
    cfg = FilterConfig(include_patterns=["nonexistent-*"])
    sf = StackFilter(cfg)
    assert sf.apply(results) == []
