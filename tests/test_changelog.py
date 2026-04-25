"""Tests for stackwatch.changelog."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from stackwatch.changelog import Changelog, ChangelogEntry, ChangelogError, render_changelog_text
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture()
def changelog_path(tmp_path: Path) -> Path:
    return tmp_path / "changelog.json"


@pytest.fixture()
def log(changelog_path: Path) -> Changelog:
    return Changelog(path=changelog_path)


def _make_result(stack_name: str, drifted: bool) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="R1", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=["Tags"])]
        if drifted
        else []
    )
    return DriftResult(stack_name=stack_name, drifted_resources=resources)


def test_load_returns_empty_when_no_file(log: Changelog) -> None:
    assert log.all_entries() == []


def test_record_creates_file(log: Changelog, changelog_path: Path) -> None:
    result = _make_result("my-stack", drifted=True)
    log.record(result, previous_state="IN_SYNC")
    assert changelog_path.exists()


def test_record_returns_none_when_state_unchanged(log: Changelog) -> None:
    result = _make_result("my-stack", drifted=True)
    entry = log.record(result, previous_state="DRIFTED")
    assert entry is None
    assert log.all_entries() == []


def test_record_returns_entry_on_transition(log: Changelog) -> None:
    result = _make_result("my-stack", drifted=True)
    entry = log.record(result, previous_state="IN_SYNC")
    assert entry is not None
    assert entry.stack_name == "my-stack"
    assert entry.previous_state == "IN_SYNC"
    assert entry.current_state == "DRIFTED"
    assert entry.drifted_count == 1


def test_record_unknown_previous_state(log: Changelog) -> None:
    result = _make_result("stack-a", drifted=False)
    entry = log.record(result)
    assert entry is not None
    assert entry.previous_state == "UNKNOWN"
    assert entry.current_state == "IN_SYNC"


def test_entries_for_filters_by_stack(log: Changelog) -> None:
    log.record(_make_result("stack-a", drifted=True), previous_state="IN_SYNC")
    log.record(_make_result("stack-b", drifted=True), previous_state="IN_SYNC")
    assert len(log.entries_for("stack-a")) == 1
    assert log.entries_for("stack-a")[0].stack_name == "stack-a"


def test_round_trip_persistence(changelog_path: Path) -> None:
    log1 = Changelog(path=changelog_path)
    log1.record(_make_result("stack-x", drifted=True), previous_state="IN_SYNC")
    log2 = Changelog(path=changelog_path)
    assert len(log2.all_entries()) == 1
    assert log2.all_entries()[0].stack_name == "stack-x"


def test_clear_removes_all_entries(log: Changelog) -> None:
    log.record(_make_result("stack-a", drifted=True), previous_state="IN_SYNC")
    log.clear()
    assert log.all_entries() == []


def test_load_raises_on_corrupt_file(changelog_path: Path) -> None:
    changelog_path.write_text("not json")
    with pytest.raises(ChangelogError):
        Changelog(path=changelog_path)


def test_render_text_contains_stack_name(log: Changelog) -> None:
    log.record(_make_result("my-stack", drifted=True), previous_state="IN_SYNC")
    text = render_changelog_text(log)
    assert "my-stack" in text
    assert "IN_SYNC" in text
    assert "DRIFTED" in text


def test_render_text_empty(log: Changelog) -> None:
    text = render_changelog_text(log)
    assert "No changelog entries" in text
