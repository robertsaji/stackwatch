"""Tests for stackwatch.trend."""
import pytest
from stackwatch.trend import build_trend, render_trend_text, TrendReport
from stackwatch.history import HistoryEntry
from stackwatch.drift import DriftResult, DriftedResource


def _make_entry(timestamp: str, drifted: int, total: int) -> HistoryEntry:
    results = []
    for i in range(total):
        has = i < drifted
        resources = [
            DriftedResource(logical_id="R", resource_type="T", drift_status="MODIFIED", expected={}, actual={})
        ] if has else []
        results.append(DriftResult(stack_name=f"stack-{i}", has_drift=has, drifted_resources=resources))
    return HistoryEntry(timestamp=timestamp, results=results)


def test_build_trend_empty():
    report = build_trend([])
    assert report.points == []


def test_build_trend_single_point():
    entry = _make_entry("2024-01-01T00:00:00", drifted=2, total=5)
    report = build_trend([entry])
    assert len(report.points) == 1
    assert report.points[0].drifted_stacks == 2
    assert report.points[0].total_stacks == 5


def test_drift_rate_calculation():
    entry = _make_entry("2024-01-01T00:00:00", drifted=1, total=4)
    report = build_trend([entry])
    assert report.points[0].drift_rate == pytest.approx(0.25)


def test_trend_improving():
    entries = [
        _make_entry("2024-01-01T00:00:00", drifted=4, total=5),
        _make_entry("2024-01-02T00:00:00", drifted=1, total=5),
    ]
    report = build_trend(entries)
    assert report.improving is True
    assert report.worsening is False


def test_trend_worsening():
    entries = [
        _make_entry("2024-01-01T00:00:00", drifted=1, total=5),
        _make_entry("2024-01-02T00:00:00", drifted=4, total=5),
    ]
    report = build_trend(entries)
    assert report.worsening is True
    assert report.improving is False


def test_render_trend_text_empty():
    report = TrendReport(points=[])
    text = render_trend_text(report)
    assert "No trend data" in text


def test_render_trend_text_contains_timestamps():
    entry = _make_entry("2024-01-01T00:00:00", drifted=2, total=4)
    report = build_trend([entry])
    text = render_trend_text(report)
    assert "2024-01-01T00:00:00" in text
    assert "50%" in text
