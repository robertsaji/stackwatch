"""Tests for stackwatch.compare."""
from unittest.mock import MagicMock
from stackwatch.compare import compare_snapshots, render_compare_text, CompareReport
from stackwatch.drift import DriftResult


def _make_snap(drifted_names, clean_names=None):
    clean_names = clean_names or []
    snap = MagicMock()
    all_names = drifted_names + clean_names
    snap.stack_names.return_value = all_names
    snap.drifted.return_value = drifted_names
    return snap


def test_newly_drifted():
    before = _make_snap([])
    after = _make_snap(["stack-a"])
    report = compare_snapshots(before, after)
    assert report.newly_drifted == ["stack-a"]
    assert report.resolved == []
    assert report.has_changes is True


def test_resolved():
    before = _make_snap(["stack-a"])
    after = _make_snap([], clean_names=["stack-a"])
    report = compare_snapshots(before, after)
    assert report.resolved == ["stack-a"]
    assert report.newly_drifted == []
    assert report.has_changes is True


def test_still_drifted():
    before = _make_snap(["stack-a"])
    after = _make_snap(["stack-a"])
    report = compare_snapshots(before, after)
    assert report.still_drifted == ["stack-a"]
    assert report.has_changes is False


def test_no_changes():
    before = _make_snap([], clean_names=["stack-a"])
    after = _make_snap([], clean_names=["stack-a"])
    report = compare_snapshots(before, after)
    assert not report.has_changes
    assert report.unchanged_clean == ["stack-a"]


def test_render_text_contains_newly_drifted():
    report = CompareReport(newly_drifted=["stack-x"], resolved=[], still_drifted=[])
    text = render_compare_text(report)
    assert "stack-x" in text
    assert "Newly drifted" in text


def test_render_text_no_changes_message():
    report = CompareReport()
    text = render_compare_text(report)
    assert "No changes" in text


def test_render_text_resolved():
    report = CompareReport(resolved=["stack-y"])
    text = render_compare_text(report)
    assert "Resolved" in text
    assert "stack-y" in text
