"""Tests for stackwatch.annotation."""
from __future__ import annotations

import pytest
from pathlib import Path

from stackwatch.annotation import Annotation, AnnotationStore, AnnotationError


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "annotations.json"


@pytest.fixture
def store(store_path: Path) -> AnnotationStore:
    return AnnotationStore(store_path)


def _make_ann(stack: str = "my-stack", note: str = "hello") -> Annotation:
    return Annotation(stack_name=stack, note=note, author="tester", created_at="2024-01-01T00:00:00")


def test_load_returns_empty_when_no_file(store: AnnotationStore) -> None:
    assert store.all_stack_names() == []


def test_add_and_get_round_trip(store: AnnotationStore) -> None:
    ann = _make_ann()
    store.add(ann)
    results = store.get("my-stack")
    assert len(results) == 1
    assert results[0].note == "hello"
    assert results[0].author == "tester"


def test_get_returns_empty_for_unknown(store: AnnotationStore) -> None:
    assert store.get("no-such-stack") == []


def test_multiple_annotations_accumulate(store: AnnotationStore) -> None:
    store.add(_make_ann(note="first"))
    store.add(_make_ann(note="second"))
    assert len(store.get("my-stack")) == 2


def test_remove_all_clears_stack(store: AnnotationStore) -> None:
    store.add(_make_ann())
    removed = store.remove_all("my-stack")
    assert removed == 1
    assert store.get("my-stack") == []


def test_remove_all_returns_zero_for_unknown(store: AnnotationStore) -> None:
    assert store.remove_all("ghost") == 0


def test_persists_to_disk(store_path: Path) -> None:
    s1 = AnnotationStore(store_path)
    s1.add(_make_ann())
    s2 = AnnotationStore(store_path)
    assert len(s2.get("my-stack")) == 1


def test_load_raises_on_corrupt_file(store_path: Path) -> None:
    store_path.write_text("not json")
    with pytest.raises(AnnotationError):
        AnnotationStore(store_path)


def test_all_stack_names(store: AnnotationStore) -> None:
    store.add(_make_ann(stack="stack-a"))
    store.add(_make_ann(stack="stack-b"))
    names = store.all_stack_names()
    assert set(names) == {"stack-a", "stack-b"}
