"""Tests for stackwatch.snapshot."""
import time
from pathlib import Path

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.snapshot import DriftSnapshot, Snapshot, SnapshotError


def _make_result(name: str, drifted: bool) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="R1", resource_type="AWS::S3::Bucket", status="MODIFIED")]
        if drifted
        else []
    )
    return DriftResult(stack_name=name, has_drift=drifted, resources=resources)


@pytest.fixture()
def snap_path(tmp_path: Path) -> Path:
    return tmp_path / "snapshots" / "drift.json"


@pytest.fixture()
def snap(snap_path: Path) -> DriftSnapshot:
    return DriftSnapshot(snap_path)


def test_load_returns_none_when_missing(snap: DriftSnapshot) -> None:
    assert snap.load() is None


def test_save_creates_file(snap: DriftSnapshot, snap_path: Path) -> None:
    snap.save([_make_result("stack-a", False)])
    assert snap_path.exists()


def test_save_and_load_round_trip(snap: DriftSnapshot) -> None:
    results = [_make_result("stack-a", True), _make_result("stack-b", False)]
    snap.save(results)
    loaded = snap.load()
    assert loaded is not None
    assert len(loaded.results) == 2
    names = loaded.stack_names()
    assert "stack-a" in names
    assert "stack-b" in names


def test_loaded_snapshot_has_timestamp(snap: DriftSnapshot) -> None:
    before = time.time()
    snap.save([_make_result("stack-a", False)])
    loaded = snap.load()
    assert loaded is not None
    assert loaded.timestamp >= before


def test_drifted_filters_correctly(snap: DriftSnapshot) -> None:
    results = [_make_result("stack-a", True), _make_result("stack-b", False)]
    snap.save(results)
    loaded = snap.load()
    assert loaded is not None
    assert len(loaded.drifted()) == 1
    assert loaded.drifted()[0].stack_name == "stack-a"


def test_diff_returns_empty_when_no_previous(snap: DriftSnapshot) -> None:
    current = [_make_result("stack-a", True)]
    assert snap.diff(current) == {}


def test_diff_detects_new_drift(snap: DriftSnapshot) -> None:
    snap.save([_make_result("stack-a", False)])
    current = [_make_result("stack-a", True)]
    changes = snap.diff(current)
    assert changes["stack-a"] == "drifted"


def test_diff_detects_resolved_drift(snap: DriftSnapshot) -> None:
    snap.save([_make_result("stack-a", True)])
    current = [_make_result("stack-a", False)]
    changes = snap.diff(current)
    assert changes["stack-a"] == "resolved"


def test_diff_detects_new_stack(snap: DriftSnapshot) -> None:
    snap.save([_make_result("stack-a", False)])
    current = [_make_result("stack-a", False), _make_result("stack-b", True)]
    changes = snap.diff(current)
    assert changes["stack-b"] == "new"
    assert "stack-a" not in changes


def test_load_raises_snapshot_error_on_corrupt_file(snap_path: Path) -> None:
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    snap_path.write_text("not json{{{")
    snap = DriftSnapshot(snap_path)
    with pytest.raises(SnapshotError):
        snap.load()
