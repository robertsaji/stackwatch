"""Tests for stackwatch.runbook."""
from __future__ import annotations

import pytest
from pathlib import Path

from stackwatch.runbook import RunbookError, RunbookStore


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "runbooks.json"


@pytest.fixture
def store(store_path: Path) -> RunbookStore:
    return RunbookStore(path=store_path)


def test_load_returns_empty_when_no_file(store: RunbookStore) -> None:
    assert store.all() == {}


def test_set_and_get_round_trip(store: RunbookStore) -> None:
    store.set("my-stack", "https://wiki.example.com/runbook")
    assert store.get("my-stack") == "https://wiki.example.com/runbook"


def test_get_returns_none_for_unknown(store: RunbookStore) -> None:
    assert store.get("nonexistent") is None


def test_set_persists_to_disk(store_path: Path) -> None:
    s1 = RunbookStore(path=store_path)
    s1.set("stack-a", "https://example.com/a")
    s2 = RunbookStore(path=store_path)
    assert s2.get("stack-a") == "https://example.com/a"


def test_remove_existing_returns_true(store: RunbookStore) -> None:
    store.set("stack-b", "https://example.com/b")
    assert store.remove("stack-b") is True
    assert store.get("stack-b") is None


def test_remove_missing_returns_false(store: RunbookStore) -> None:
    assert store.remove("ghost") is False


def test_invalid_url_raises(store: RunbookStore) -> None:
    with pytest.raises(RunbookError, match="Invalid URL"):
        store.set("stack-c", "ftp://bad-scheme")


def test_all_returns_copy(store: RunbookStore) -> None:
    store.set("s1", "https://a.com")
    store.set("s2", "https://b.com")
    data = store.all()
    assert len(data) == 2
    data["s3"] = "https://c.com"
    assert store.get("s3") is None
