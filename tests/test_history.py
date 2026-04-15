"""Tests for stackwatch.history."""

import json
from pathlib import Path

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.history import DriftHistory, HistoryEntry, HistoryError


@pytest.fixture()
def history_path(tmp_path: Path) -> Path:
    return tmp_path / "history" / "drift.jsonl"


@pytest.fixture()
def history(history_path: Path) -> DriftHistory:
    return DriftHistory(history_path)


def _make_result(stack_name: str = "my-stack", drifted: bool = True) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="Res1", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=[])]
        if drifted
        else []
    )
    return DriftResult(
        stack_name=stack_name,
        region="us-east-1",
        drifted=drifted,
        drifted_resources=resources,
    )


def test_load_returns_empty_when_no_file(history: DriftHistory) -> None:
    assert history.load() == []


def test_record_creates_file(history: DriftHistory, history_path: Path) -> None:
    history.record(_make_result())
    assert history_path.exists()


def test_record_returns_entry(history: DriftHistory) -> None:
    entry = history.record(_make_result(drifted=True))
    assert isinstance(entry, HistoryEntry)
    assert entry.stack_name == "my-stack"
    assert entry.drifted is True
    assert entry.drifted_resource_count == 1


def test_round_trip_single_entry(history: DriftHistory) -> None:
    history.record(_make_result(stack_name="stack-a", drifted=False))
    entries = history.load()
    assert len(entries) == 1
    assert entries[0].stack_name == "stack-a"
    assert entries[0].drifted is False
    assert entries[0].drifted_resource_count == 0


def test_multiple_records_appended(history: DriftHistory) -> None:
    history.record(_make_result(stack_name="stack-1"))
    history.record(_make_result(stack_name="stack-2"))
    history.record(_make_result(stack_name="stack-1"))
    assert len(history.load()) == 3


def test_filter_by_stack_name(history: DriftHistory) -> None:
    history.record(_make_result(stack_name="alpha"))
    history.record(_make_result(stack_name="beta"))
    history.record(_make_result(stack_name="alpha"))
    results = history.load(stack_name="alpha")
    assert len(results) == 2
    assert all(e.stack_name == "alpha" for e in results)


def test_clear_removes_file(history: DriftHistory, history_path: Path) -> None:
    history.record(_make_result())
    assert history_path.exists()
    history.clear()
    assert not history_path.exists()


def test_clear_on_missing_file_is_noop(history: DriftHistory) -> None:
    history.clear()  # should not raise


def test_corrupt_line_raises_history_error(history: DriftHistory, history_path: Path) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text("not-valid-json\n", encoding="utf-8")
    with pytest.raises(HistoryError):
        history.load()
