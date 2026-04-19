"""Tests for stackwatch.annotation_cli."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from stackwatch.annotation_cli import annotation_group


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def store_file(tmp_path: Path) -> str:
    return str(tmp_path / "annotations.json")


def test_list_empty(runner: CliRunner, store_file: str) -> None:
    result = runner.invoke(annotation_group, ["list", "my-stack", "--store", store_file])
    assert result.exit_code == 0
    assert "No annotations" in result.output


def test_add_annotation(runner: CliRunner, store_file: str) -> None:
    result = runner.invoke(
        annotation_group,
        ["add", "my-stack", "This stack is critical", "--author", "alice", "--store", store_file],
    )
    assert result.exit_code == 0
    assert "added" in result.output


def test_list_after_add(runner: CliRunner, store_file: str) -> None:
    runner.invoke(annotation_group, ["add", "my-stack", "note1", "--store", store_file])
    result = runner.invoke(annotation_group, ["list", "my-stack", "--store", store_file])
    assert "note1" in result.output


def test_clear_annotations(runner: CliRunner, store_file: str) -> None:
    runner.invoke(annotation_group, ["add", "my-stack", "note1", "--store", store_file])
    result = runner.invoke(annotation_group, ["clear", "my-stack", "--store", store_file])
    assert result.exit_code == 0
    assert "Removed 1" in result.output


def test_clear_unknown_stack(runner: CliRunner, store_file: str) -> None:
    result = runner.invoke(annotation_group, ["clear", "ghost", "--store", store_file])
    assert result.exit_code == 0
    assert "Removed 0" in result.output
