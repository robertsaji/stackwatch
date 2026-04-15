"""Tests for stackwatch.tags."""
from __future__ import annotations

import pytest

from stackwatch.drift import DriftResult
from stackwatch.tags import TagFilter, drift_rate_by_tag, group_by_tag


def _make_result(name: str, has_drift: bool, tags: dict | None = None) -> DriftResult:
    return DriftResult(
        stack_name=name,
        has_drift=has_drift,
        drifted_resources=[],
        stack_tags=tags or {},
    )


@pytest.fixture()
def results():
    return [
        _make_result("app-prod", True, {"env": "prod", "team": "platform"}),
        _make_result("app-staging", False, {"env": "staging", "team": "platform"}),
        _make_result("db-prod", True, {"env": "prod", "team": "data"}),
        _make_result("orphan", False, {}),
    ]


# --- TagFilter.matches ---

def test_matches_key_exists_any_value():
    tf = TagFilter(required_tags={"env": None})
    assert tf.matches({"env": "prod"}) is True
    assert tf.matches({"other": "x"}) is False


def test_matches_key_exact_value():
    tf = TagFilter(required_tags={"env": "prod"})
    assert tf.matches({"env": "prod"}) is True
    assert tf.matches({"env": "staging"}) is False


def test_matches_empty_filter_accepts_all():
    tf = TagFilter()
    assert tf.matches({}) is True
    assert tf.matches({"env": "prod"}) is True


def test_matches_multiple_constraints():
    tf = TagFilter(required_tags={"env": "prod", "team": None})
    assert tf.matches({"env": "prod", "team": "platform"}) is True
    assert tf.matches({"env": "prod"}) is False


# --- TagFilter.apply ---

def test_apply_filters_results(results):
    tf = TagFilter(required_tags={"env": "prod"})
    filtered = tf.apply(results)
    assert len(filtered) == 2
    assert all(r.stack_tags.get("env") == "prod" for r in filtered)


def test_apply_empty_filter_returns_all(results):
    tf = TagFilter()
    assert tf.apply(results) == results


# --- group_by_tag ---

def test_group_by_tag_groups_correctly(results):
    groups = group_by_tag(results, "env")
    assert set(groups.keys()) == {"prod", "staging", "<untagged>"}
    assert len(groups["prod"]) == 2
    assert len(groups["staging"]) == 1
    assert len(groups["<untagged>"]) == 1


def test_group_by_tag_missing_key_untagged():
    r = _make_result("x", False, {})
    groups = group_by_tag([r], "env")
    assert "<untagged>" in groups


# --- drift_rate_by_tag ---

def test_drift_rate_by_tag(results):
    rates = drift_rate_by_tag(results, "env")
    assert rates["prod"] == pytest.approx(1.0)
    assert rates["staging"] == pytest.approx(0.0)


def test_drift_rate_by_tag_untagged(results):
    rates = drift_rate_by_tag(results, "env")
    assert rates["<untagged>"] == pytest.approx(0.0)
