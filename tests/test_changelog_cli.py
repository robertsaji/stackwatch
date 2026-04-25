"""Tests for stackwatch.changelog_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from stackwatch.changelog_cli import changelog_group
from stackwatch.changelog import Changelog
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def store_file(tmp_path: Path) -> str:
    return str(tmp_path / "changelog.json")


def _seed(store_file: str) -> None:
    """Seed one entry into the changelog."""
    from stackwatch.changelog import Changelog
    from stackwatch.drift import DriftResult, DriftedResource

    log = Changelog(path=Path(store_file))
    result = DriftResult(
        stack_name="seed-stack",
        drifted_resources=[DriftedResource(logical_id="R", resource_type="AWS::EC2::Instance", status="MODIFIED", properties=[])],
    )
    log.record(result, previous_state="IN_SYNC")


def test_list_empty(runner: CliRunner, store_file: str) -> None:
    result = runner.invoke(changelog_group, ["list", "--file", store_file])
    assert result.exit_code == 0
    assert "No changelog entries" in result.output


def test_list_shows_entries(runner: CliRunner, store_file: str) -> None:
    _seed(store_file)
    result = runner.invoke(changelog_group, ["list", "--file", store_file])
    assert result.exit_code == 0
    assert "seed-stack" in result.output


def test_list_filters_by_stack(runner: CliRunner, store_file: str) -> None:
    _seed(store_file)
    result = runner.invoke(changelog_group, ["list", "--file", store_file, "--stack", "other-stack"])
    assert result.exit_code == 0
    assert "seed-stack" not in result.output


def test_show_command(runner: CliRunner, store_file: str) -> None:
    _seed(store_file)
    result = runner.invoke(changelog_group, ["show", "--file", store_file])
    assert result.exit_code == 0
    assert "Drift Changelog" in result.output


def test_clear_command(runner: CliRunner, store_file: str) -> None:
    _seed(store_file)
    result = runner.invoke(changelog_group, ["clear", "--file", store_file], input="y\n")
    assert result.exit_code == 0
    assert "cleared" in result.output.lower()
    log = Changelog(path=Path(store_file))
    assert log.all_entries() == []
