"""Tests for stackwatch.ttl."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from stackwatch.drift import DriftResult
from stackwatch.ttl import (
    TTLConfig,
    TTLError,
    apply_ttl,
    render_ttl_text,
)


def _make_result(stack_name: str, drifted: bool = False) -> DriftResult:
    return DriftResult(stack_name=stack_name, drifted=drifted, resources=[])


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# TTLConfig validation
# ---------------------------------------------------------------------------

def test_invalid_max_age_raises() -> None:
    with pytest.raises(TTLError):
        TTLConfig(max_age_seconds=0)


def test_negative_max_age_raises() -> None:
    with pytest.raises(TTLError):
        TTLConfig(max_age_seconds=-60)


def test_valid_config_does_not_raise() -> None:
    cfg = TTLConfig(max_age_seconds=300)
    assert cfg.max_age_seconds == 300


# ---------------------------------------------------------------------------
# apply_ttl
# ---------------------------------------------------------------------------

def test_result_detected_now_is_fresh() -> None:
    result = _make_result("stack-a", drifted=True)
    report = apply_ttl([result], {"stack-a": _now()}, TTLConfig(max_age_seconds=60))
    assert len(report.fresh) == 1
    assert len(report.stale) == 0


def test_result_detected_long_ago_is_stale() -> None:
    result = _make_result("stack-b", drifted=True)
    old = _now() - timedelta(hours=2)
    report = apply_ttl([result], {"stack-b": old}, TTLConfig(max_age_seconds=3600))
    assert len(report.stale) == 1
    assert len(report.fresh) == 0


def test_missing_detected_at_defaults_to_now_and_is_fresh() -> None:
    result = _make_result("stack-c")
    report = apply_ttl([result], {}, TTLConfig(max_age_seconds=60))
    assert report.entries[0].is_fresh is True


def test_mixed_fresh_and_stale() -> None:
    r1 = _make_result("fresh-stack", drifted=True)
    r2 = _make_result("stale-stack", drifted=True)
    detected = {
        "fresh-stack": _now() - timedelta(seconds=10),
        "stale-stack": _now() - timedelta(seconds=7200),
    }
    report = apply_ttl([r1, r2], detected, TTLConfig(max_age_seconds=3600))
    assert len(report.fresh) == 1
    assert len(report.stale) == 1
    assert report.fresh[0].result.stack_name == "fresh-stack"
    assert report.stale[0].result.stack_name == "stale-stack"


def test_age_seconds_is_positive() -> None:
    result = _make_result("stack-d")
    old = _now() - timedelta(minutes=5)
    report = apply_ttl([result], {"stack-d": old}, TTLConfig(max_age_seconds=600))
    assert report.entries[0].age_seconds > 0


def test_naive_datetime_handled() -> None:
    result = _make_result("stack-e")
    naive = datetime.utcnow() - timedelta(seconds=30)
    report = apply_ttl([result], {"stack-e": naive}, TTLConfig(max_age_seconds=60))
    assert report.entries[0].is_fresh is True


# ---------------------------------------------------------------------------
# render_ttl_text
# ---------------------------------------------------------------------------

def test_render_text_contains_stack_name() -> None:
    result = _make_result("my-stack", drifted=True)
    report = apply_ttl([result], {"my-stack": _now()}, TTLConfig(max_age_seconds=60))
    text = render_ttl_text(report)
    assert "my-stack" in text


def test_render_text_shows_fresh_stale_counts() -> None:
    r1 = _make_result("s1")
    r2 = _make_result("s2")
    detected = {
        "s1": _now(),
        "s2": _now() - timedelta(hours=5),
    }
    report = apply_ttl([r1, r2], detected, TTLConfig(max_age_seconds=3600))
    text = render_ttl_text(report)
    assert "1 fresh" in text
    assert "1 stale" in text
