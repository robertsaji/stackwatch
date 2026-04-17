"""Tests for stackwatch.dependency."""
from __future__ import annotations

import pytest
from pathlib import Path

from stackwatch.dependency import DependencyStore, DependencyError


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "deps.json"


@pytest.fixture
def store(store_path: Path) -> DependencyStore:
    return DependencyStore(path=store_path)


def test_load_returns_empty_when_no_file(store: DependencyStore) -> None:
    assert store.all_stacks() == []


def test_add_and_list_dependencies(store: DependencyStore) -> None:
    store.add("app", "vpc")
    store.add("app", "db")
    assert store.dependencies("app") == ["db", "vpc"]


def test_add_persists_to_disk(store_path: Path) -> None:
    s1 = DependencyStore(path=store_path)
    s1.add("app", "vpc")
    s2 = DependencyStore(path=store_path)
    assert "vpc" in s2.dependencies("app")


def test_remove_dependency(store: DependencyStore) -> None:
    store.add("app", "vpc")
    store.add("app", "db")
    store.remove("app", "vpc")
    assert store.dependencies("app") == ["db"]


def test_remove_last_dep_clears_stack(store: DependencyStore) -> None:
    store.add("app", "vpc")
    store.remove("app", "vpc")
    assert store.all_stacks() == []


def test_dependents(store: DependencyStore) -> None:
    store.add("app", "vpc")
    store.add("api", "vpc")
    assert store.dependents("vpc") == ["api", "app"]


def test_dependents_empty_when_none(store: DependencyStore) -> None:
    store.add("app", "vpc")
    assert store.dependents("app") == []


def test_clear_removes_all_edges(store: DependencyStore) -> None:
    store.add("app", "vpc")
    store.add("app", "db")
    store.clear("app")
    assert store.dependencies("app") == []
    assert store.all_stacks() == []


def test_load_raises_on_corrupt_file(store_path: Path) -> None:
    store_path.write_text("not json")
    with pytest.raises(DependencyError):
        DependencyStore(path=store_path)
