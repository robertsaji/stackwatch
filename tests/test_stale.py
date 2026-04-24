"""Tests for stackwatch.stale."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

import pytest

from stackwatch.drift import DriftResult
from stackwatch.history import HistoryEntry
from stackwatch.stale import (
    StaleConfig,
    StaleError,
    build_stale_report,
    render_stale_text,
)


def _make_result(name: str) -> DriftResult:
    return DriftResult(stack_name=name, drifted=False, resources=[])


def _make_entry(name: str, hours_ago: float) -> HistoryEntry:
    ts = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
    return HistoryEntry(stack_name=name, timestamp=ts, drifted=False, resource_count=0)


# --- config validation ---

def test_invalid_max_age_raises() -> None:
    with pytest.raises(StaleError):
        StaleConfig(max_age_hours=0)


def test_negative_max_age_raises() -> None:
    with pytest.raises(StaleError):
        StaleConfig(max_age_hours=-1)


# --- build_stale_report ---

def test_no_history_marks_all_stale() -> None:
    results = [_make_result("stack-a"), _make_result("stack-b")]
    report = build_stale_report(results, [], StaleConfig(max_age_hours=24))
    assert report.stale_count == 2
    assert report.total == 2


def test_fresh_stack_not_stale() -> None:
    results = [_make_result("stack-a")]
    history = [_make_entry("stack-a", hours_ago=1)]
    report = build_stale_report(results, history, StaleConfig(max_age_hours=24))
    assert report.stale_count == 0
    assert len(report.fresh) == 1


def test_old_stack_is_stale() -> None:
    results = [_make_result("stack-a")]
    history = [_make_entry("stack-a", hours_ago=48)]
    report = build_stale_report(results, history, StaleConfig(max_age_hours=24))
    assert report.stale_count == 1
    assert report.fresh == []


def test_mixed_stacks() -> None:
    results = [_make_result("fresh"), _make_result("stale"), _make_result("never")]
    history = [
        _make_entry("fresh", hours_ago=2),
        _make_entry("stale", hours_ago=30),
    ]
    report = build_stale_report(results, history, StaleConfig(max_age_hours=24))
    assert report.stale_count == 2
    assert len(report.fresh) == 1
    assert report.fresh[0].stack_name == "fresh"


def test_uses_most_recent_history_entry() -> None:
    results = [_make_result("stack-a")]
    history = [
        _make_entry("stack-a", hours_ago=48),
        _make_entry("stack-a", hours_ago=1),
    ]
    report = build_stale_report(results, history, StaleConfig(max_age_hours=24))
    assert report.stale_count == 0


def test_age_hours_populated() -> None:
    results = [_make_result("stack-a")]
    history = [_make_entry("stack-a", hours_ago=5)]
    report = build_stale_report(results, history, StaleConfig(max_age_hours=24))
    sr = report.fresh[0]
    assert sr.age_hours is not None
    assert 4.9 < sr.age_hours < 5.1


# --- render_stale_text ---

def test_render_text_contains_stack_name() -> None:
    results = [_make_result("my-stack")]
    report = build_stale_report(results, [], StaleConfig(max_age_hours=24))
    text = render_stale_text(report)
    assert "my-stack" in text


def test_render_text_shows_never_for_no_history() -> None:
    results = [_make_result("my-stack")]
    report = build_stale_report(results, [], StaleConfig(max_age_hours=24))
    text = render_stale_text(report)
    assert "never" in text
