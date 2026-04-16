"""Tests for stackwatch.suppression_cli."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from stackwatch.suppression_cli import suppress_group


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def store_file(tmp_path: Path) -> str:
    return str(tmp_path / "suppressions.json")


def test_add_rule(runner: CliRunner, store_file: str):
    result = runner.invoke(suppress_group, ["--store", store_file, "add", "my-stack", "--reason", "planned"])
    assert result.exit_code == 0
    assert "my-stack" in result.output


def test_list_empty(runner: CliRunner, store_file: str):
    result = runner.invoke(suppress_group, ["--store", store_file, "list"])
    assert result.exit_code == 0
    assert "No active" in result.output


def test_list_after_add(runner: CliRunner, store_file: str):
    runner.invoke(suppress_group, ["--store", store_file, "add", "stack-a", "--reason", "ok"])
    result = runner.invoke(suppress_group, ["--store", store_file, "list"])
    assert result.exit_code == 0
    assert "stack-a" in result.output


def test_remove_existing(runner: CliRunner, store_file: str):
    runner.invoke(suppress_group, ["--store", store_file, "add", "stack-a", "--reason", "ok"])
    result = runner.invoke(suppress_group, ["--store", store_file, "remove", "stack-a"])
    assert result.exit_code == 0
    assert "removed" in result.output


def test_remove_nonexistent(runner: CliRunner, store_file: str):
    result = runner.invoke(suppress_group, ["--store", store_file, "remove", "ghost"])
    assert result.exit_code == 0
    assert "No suppression found" in result.output


def test_add_with_expiry(runner: CliRunner, store_file: str):
    result = runner.invoke(
        suppress_group,
        ["--store", store_file, "add", "stack-b", "--reason", "temp", "--expires-at", "2099-01-01T00:00:00+00:00"]
    )
    assert result.exit_code == 0
    list_result = runner.invoke(suppress_group, ["--store", store_file, "list"])
    assert "stack-b" in list_result.output
