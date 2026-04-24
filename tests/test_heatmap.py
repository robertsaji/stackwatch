"""Tests for stackwatch.heatmap."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from stackwatch.heatmap import (
    Heatmap,
    HeatmapCell,
    build_heatmap,
    render_heatmap_text,
)
from stackwatch.history import HistoryEntry


def _entry(stack: str, drifted: bool) -> HistoryEntry:
    return HistoryEntry(
        stack_name=stack,
        checked_at=datetime.now(tz=timezone.utc).isoformat(),
        drifted=drifted,
        drifted_resource_count=1 if drifted else 0,
    )


@pytest.fixture()
def entries() -> List[HistoryEntry]:
    return [
        _entry("stack-a", drifted=True),
        _entry("stack-a", drifted=True),
        _entry("stack-a", drifted=False),
        _entry("stack-b", drifted=False),
        _entry("stack-b", drifted=False),
    ]


def test_build_heatmap_counts(entries):
    heatmap = build_heatmap(entries)
    assert heatmap.total_stacks == 2
    by_name = {c.stack_name: c for c in heatmap.cells}
    assert by_name["stack-a"].total_checks == 3
    assert by_name["stack-a"].drifted_checks == 2
    assert by_name["stack-b"].total_checks == 2
    assert by_name["stack-b"].drifted_checks == 0


def test_build_heatmap_empty():
    heatmap = build_heatmap([])
    assert heatmap.total_stacks == 0
    assert heatmap.cells == []


def test_drift_rate_calculation(entries):
    heatmap = build_heatmap(entries)
    by_name = {c.stack_name: c for c in heatmap.cells}
    assert by_name["stack-a"].drift_rate == pytest.approx(2 / 3)
    assert by_name["stack-b"].drift_rate == pytest.approx(0.0)


def test_heat_labels():
    assert HeatmapCell("x", 1, 0).heat_label == "none"
    assert HeatmapCell("x", 4, 1).heat_label == "low"       # 0.25 boundary
    assert HeatmapCell("x", 10, 4).heat_label == "medium"   # 0.40
    assert HeatmapCell("x", 10, 8).heat_label == "high"     # 0.80
    assert HeatmapCell("x", 1, 1).heat_label == "critical"  # 1.0


def test_hottest_returns_sorted(entries):
    heatmap = build_heatmap(entries)
    hottest = heatmap.hottest(2)
    assert hottest[0].stack_name == "stack-a"
    assert hottest[1].stack_name == "stack-b"


def test_hottest_clamps_to_available(entries):
    heatmap = build_heatmap(entries)
    assert len(heatmap.hottest(100)) == 2


def test_render_text_contains_headers(entries):
    heatmap = build_heatmap(entries)
    text = render_heatmap_text(heatmap)
    assert "Stack" in text
    assert "Checks" in text
    assert "Drifted" in text
    assert "Rate" in text
    assert "Heat" in text


def test_render_text_contains_stack_names(entries):
    heatmap = build_heatmap(entries)
    text = render_heatmap_text(heatmap)
    assert "stack-a" in text
    assert "stack-b" in text


def test_render_text_empty():
    text = render_heatmap_text(Heatmap(cells=[]))
    assert "No heatmap data" in text
