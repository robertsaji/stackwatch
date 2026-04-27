"""Tests for stackwatch.dedup."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from stackwatch.dedup import DedupStore, _fingerprint
from stackwatch.drift import DriftResult, DriftedResource


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_result(stack: str, drifted: bool = True) -> DriftResult:
    resources = (
        [DriftedResource(resource_id="res-1", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})]
        if drifted
        else []
    )
    return DriftResult(stack_name=stack, drifted_resources=resources)


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "dedup.json"


@pytest.fixture()
def store(store_path: Path) -> DedupStore:
    return DedupStore(path=store_path)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_no_file(store: DedupStore) -> None:
    assert store.all_entries() == []


def test_is_duplicate_returns_false_for_in_sync(store: DedupStore) -> None:
    result = _make_result("my-stack", drifted=False)
    assert store.is_duplicate(result) is False


def test_is_duplicate_returns_false_before_record(store: DedupStore) -> None:
    result = _make_result("my-stack", drifted=True)
    assert store.is_duplicate(result) is False


def test_is_duplicate_returns_true_after_record(store: DedupStore) -> None:
    result = _make_result("my-stack", drifted=True)
    store.record(result)
    assert store.is_duplicate(result) is True


def test_record_persists_to_disk(store_path: Path, store: DedupStore) -> None:
    result = _make_result("my-stack", drifted=True)
    store.record(result)
    assert store_path.exists()
    data = json.loads(store_path.read_text())
    assert "my-stack" in data


def test_record_in_sync_removes_entry(store: DedupStore) -> None:
    drifted = _make_result("my-stack", drifted=True)
    store.record(drifted)
    assert store.is_duplicate(drifted) is True

    resolved = _make_result("my-stack", drifted=False)
    store.record(resolved)
    assert store.is_duplicate(drifted) is False
    assert store.all_entries() == []


def test_different_resources_not_duplicate(store: DedupStore) -> None:
    result_a = _make_result("my-stack", drifted=True)
    store.record(result_a)

    # Build a result with a different resource id
    result_b = DriftResult(
        stack_name="my-stack",
        drifted_resources=[
            DriftedResource(
                resource_id="res-99",
                resource_type="AWS::EC2::Instance",
                drift_status="MODIFIED",
                expected={},
                actual={},
            )
        ],
    )
    assert store.is_duplicate(result_b) is False


def test_clear_single_stack(store: DedupStore) -> None:
    store.record(_make_result("stack-a"))
    store.record(_make_result("stack-b"))
    store.clear("stack-a")
    names = {e.stack_name for e in store.all_entries()}
    assert "stack-a" not in names
    assert "stack-b" in names


def test_clear_all(store: DedupStore) -> None:
    store.record(_make_result("stack-a"))
    store.record(_make_result("stack-b"))
    store.clear()
    assert store.all_entries() == []


def test_fingerprint_stable(store: DedupStore) -> None:
    r = _make_result("my-stack")
    assert _fingerprint(r) == _fingerprint(r)
