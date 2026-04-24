"""Tests for stackwatch.grouping_cli."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from stackwatch.grouping_cli import grouping_group


@pytest.fixture()
def runner():
    return CliRunner()


def _make_mock_snap(stack_names: list[str], drifted: set[str] | None = None):
    from stackwatch.drift import DriftResult

    drifted = drifted or set()
    results = []
    for name in stack_names:
        r = DriftResult(
            stack_name=name,
            drift_status="DRIFTED" if name in drifted else "IN_SYNC",
            drifted_resources=[],
        )
        r.tags = {"Environment": name.split("-")[0]}
        results.append(r)
    snap = MagicMock()
    snap.results = results
    return snap


def test_show_groups_by_prefix(runner, tmp_path):
    snap = _make_mock_snap(["prod-api", "prod-worker", "dev-api"], drifted={"prod-api"})
    with patch("stackwatch.grouping_cli._load_snapshot", return_value=snap):
        result = runner.invoke(
            grouping_group,
            ["show", "snap.json", "--prefix-delimiter", "-"],
        )
    assert result.exit_code == 0
    assert "prod" in result.output
    assert "dev" in result.output


def test_show_groups_by_tag(runner):
    snap = _make_mock_snap(["prod-api", "staging-api"], drifted={"prod-api"})
    with patch("stackwatch.grouping_cli._load_snapshot", return_value=snap):
        result = runner.invoke(
            grouping_group,
            ["show", "snap.json", "--tag-key", "Environment"],
        )
    assert result.exit_code == 0
    assert "prod" in result.output


def test_show_invalid_config_exits_nonzero(runner):
    with patch("stackwatch.grouping_cli._load_snapshot", return_value=MagicMock(results=[])):
        result = runner.invoke(
            grouping_group,
            ["show", "snap.json", "--tag-key", "Env", "--prefix-delimiter", "-"],
        )
    assert result.exit_code != 0


def test_json_output_is_valid_json(runner):
    snap = _make_mock_snap(["prod-api", "dev-api"], drifted={"prod-api"})
    with patch("stackwatch.grouping_cli._load_snapshot", return_value=snap):
        result = runner.invoke(
            grouping_group,
            ["json", "snap.json", "--prefix-delimiter", "-"],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert all("group" in item and "drift_rate" in item for item in data)


def test_load_snapshot_raises_on_missing(runner):
    with patch("stackwatch.grouping_cli.Snapshot") as mock_snap_cls:
        mock_snap_cls.load.return_value = None
        result = runner.invoke(
            grouping_group,
            ["show", "missing.json", "--prefix-delimiter", "-"],
        )
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "Error" in result.output
