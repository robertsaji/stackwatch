"""Tests for stackwatch.ownership."""
from __future__ import annotations

import pytest
from pathlib import Path

from stackwatch.ownership import OwnershipError, OwnershipStore, annotate_results
from stackwatch.drift import DriftResult


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "ownership.json"


@pytest.fixture()
def store(store_path: Path) -> OwnershipStore:
    return OwnershipStore(store_path)


def _make_result(name: str) -> DriftResult:
    return DriftResult(stack_name=name, drifted=False, resources=[])


def test_load_returns_empty_when_no_file(store: OwnershipStore) -> None:
    assert store.all_owners() == {}


def test_set_and_get_owner(store: OwnershipStore) -> None:
    store.set_owner("my-stack", "team-a")
    assert store.get_owner("my-stack") == "team-a"


def test_set_persists_across_instances(store_path: Path) -> None:
    s1 = OwnershipStore(store_path)
    s1.set_owner("stack-x", "team-b")
    s2 = OwnershipStore(store_path)
    assert s2.get_owner("stack-x") == "team-b"


def test_remove_owner(store: OwnershipStore) -> None:
    store.set_owner("stack-y", "team-c")
    store.remove_owner("stack-y")
    assert store.get_owner("stack-y") is None


def test_remove_nonexistent_does_not_raise(store: OwnershipStore) -> None:
    store.remove_owner("ghost-stack")  # should not raise


def test_stacks_for_owner(store: OwnershipStore) -> None:
    store.set_owner("a", "team-a")
    store.set_owner("b", "team-b")
    store.set_owner("c", "team-a")
    assert sorted(store.stacks_for_owner("team-a")) == ["a", "c"]


def test_empty_stack_name_raises(store: OwnershipStore) -> None:
    with pytest.raises(OwnershipError):
        store.set_owner("", "team-a")


def test_empty_owner_raises(store: OwnershipStore) -> None:
    with pytest.raises(OwnershipError):
        store.set_owner("stack-z", "")


def test_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json")
    with pytest.raises(OwnershipError):
        OwnershipStore(p)


def test_annotate_results(store: OwnershipStore) -> None:
    store.set_owner("s1", "team-a")
    results = [_make_result("s1"), _make_result("s2")]
    annotated = annotate_results(results, store)
    assert annotated[0] == (results[0], "team-a")
    assert annotated[1] == (results[1], None)
