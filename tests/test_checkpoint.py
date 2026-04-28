"""Tests for stackwatch.checkpoint."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from stackwatch.checkpoint import Checkpoint, CheckpointError, CheckpointStore


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "cp.json"


@pytest.fixture()
def store(store_path: Path) -> CheckpointStore:
    return CheckpointStore(store_path)


def _make_checkpoint(**kwargs) -> Checkpoint:
    defaults = dict(
        run_id="run-1",
        timestamp=time.time(),
        stack_names=["stack-a", "stack-b"],
        drifted_stacks=["stack-a"],
    )
    defaults.update(kwargs)
    return Checkpoint(**defaults)


def test_load_returns_none_when_missing(store: CheckpointStore) -> None:
    assert store.load() is None


def test_save_creates_file(store: CheckpointStore, store_path: Path) -> None:
    cp = _make_checkpoint()
    store.save(cp)
    assert store_path.exists()


def test_round_trip(store: CheckpointStore) -> None:
    cp = _make_checkpoint(run_id="abc", stack_names=["s1"], drifted_stacks=[])
    store.save(cp)
    loaded = store.load()
    assert loaded is not None
    assert loaded.run_id == "abc"
    assert loaded.stack_names == ["s1"]
    assert loaded.drifted_stacks == []


def test_clear_removes_file(store: CheckpointStore, store_path: Path) -> None:
    store.save(_make_checkpoint())
    assert store_path.exists()
    store.clear()
    assert not store_path.exists()


def test_clear_is_idempotent(store: CheckpointStore) -> None:
    store.clear()  # should not raise


def test_load_raises_on_invalid_json(store: CheckpointStore, store_path: Path) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text("not-json")
    with pytest.raises(CheckpointError):
        store.load()


def test_age_seconds_is_positive(store: CheckpointStore) -> None:
    cp = _make_checkpoint(timestamp=time.time() - 10)
    store.save(cp)
    loaded = store.load()
    assert loaded is not None
    assert loaded.age_seconds >= 10


def test_metadata_persisted(store: CheckpointStore) -> None:
    cp = _make_checkpoint(metadata={"env": "prod"})
    store.save(cp)
    loaded = store.load()
    assert loaded is not None
    assert loaded.metadata == {"env": "prod"}
