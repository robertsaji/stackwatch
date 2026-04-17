"""Tests for stackwatch.label."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from stackwatch.label import LabelError, LabelStore, filter_by_label, group_by_label
from stackwatch.label_cli import label_group
from stackwatch.drift import DriftResult


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "labels.json"


@pytest.fixture()
def store(store_path: Path) -> LabelStore:
    return LabelStore(store_path)


def _make_result(name: str) -> DriftResult:
    return DriftResult(stack_name=name, drifted_resources=[], checked=True)


def test_load_returns_empty_when_no_file(store: LabelStore) -> None:
    assert store.all() == {}


def test_set_and_get_round_trip(store: LabelStore) -> None:
    store.set_labels("my-stack", ["prod", "critical"])
    assert store.get_labels("my-stack") == ["prod", "critical"]


def test_set_persists_to_disk(store_path: Path, store: LabelStore) -> None:
    store.set_labels("my-stack", ["dev"])
    reloaded = LabelStore(store_path)
    assert reloaded.get_labels("my-stack") == ["dev"]


def test_remove_clears_labels(store: LabelStore) -> None:
    store.set_labels("my-stack", ["prod"])
    store.remove("my-stack")
    assert store.get_labels("my-stack") == []


def test_get_unknown_stack_returns_empty(store: LabelStore) -> None:
    assert store.get_labels("unknown") == []


def test_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not-json")
    with pytest.raises(LabelError):
        LabelStore(p)


def test_filter_by_label(store: LabelStore) -> None:
    store.set_labels("a", ["prod"])
    store.set_labels("b", ["dev"])
    results = [_make_result("a"), _make_result("b")]
    filtered = filter_by_label(results, store, "prod")
    assert len(filtered) == 1
    assert filtered[0].stack_name == "a"


def test_group_by_label(store: LabelStore) -> None:
    store.set_labels("a", ["prod", "critical"])
    store.set_labels("b", ["prod"])
    results = [_make_result("a"), _make_result("b")]
    groups = group_by_label(results, store)
    assert len(groups["prod"]) == 2
    assert len(groups["critical"]) == 1


def test_cli_set_and_list(tmp_path: Path) -> None:
    runner = CliRunner()
    p = str(tmp_path / "labels.json")
    result = runner.invoke(label_group, ["set", "my-stack", "prod", "--store", p])
    assert result.exit_code == 0
    result = runner.invoke(label_group, ["list", "--store", p])
    assert "my-stack" in result.output
    assert "prod" in result.output


def test_cli_remove(tmp_path: Path) -> None:
    runner = CliRunner()
    p = str(tmp_path / "labels.json")
    runner.invoke(label_group, ["set", "my-stack", "prod", "--store", p])
    result = runner.invoke(label_group, ["remove", "my-stack", "--store", p])
    assert result.exit_code == 0
    result = runner.invoke(label_group, ["list", "--store", p])
    assert "No labels" in result.output
