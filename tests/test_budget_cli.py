"""Tests for stackwatch.budget_cli."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from stackwatch.budget_cli import budget_group
from stackwatch.budget import BudgetResult
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _make_snap(results: list) -> MagicMock:
    snap = MagicMock()
    snap.results = {r.stack_name: r for r in results}
    return snap


def _make_result(stack: str, drifted_count: int) -> DriftResult:
    resources = [
        DriftedResource(
            logical_id=f"Res{i}",
            resource_type="AWS::EC2::Instance",
            drift_status="MODIFIED",
            expected_properties="{}",
            actual_properties="{\"X\":1}",
        )
        for i in range(drifted_count)
    ]
    return DriftResult(
        stack_name=stack,
        drift_status="DRIFTED" if drifted_count else "IN_SYNC",
        drifted_resources=resources,
    )


def test_check_exits_zero_when_under_budget(runner, tmp_path):
    snap_file = tmp_path / "snap.json"
    snap_file.write_text("{}")
    snap = _make_snap([_make_result("stack-a", 1)])

    with patch("stackwatch.budget_cli.Snapshot.load", return_value=snap):
        result = runner.invoke(budget_group, [
            "check", str(snap_file),
            "--cost-per-resource", "5",
            "--monthly-budget", "1000",
        ])

    assert result.exit_code == 0
    assert "OK" in result.output


def test_check_exits_nonzero_when_over_budget(runner, tmp_path):
    snap_file = tmp_path / "snap.json"
    snap_file.write_text("{}")
    snap = _make_snap([_make_result("stack-a", 50)])

    with patch("stackwatch.budget_cli.Snapshot.load", return_value=snap):
        result = runner.invoke(budget_group, [
            "check", str(snap_file),
            "--cost-per-resource", "10",
            "--monthly-budget", "100",
        ])

    assert result.exit_code == 1
    assert "OVER BUDGET" in result.output


def test_check_json_output(runner, tmp_path):
    snap_file = tmp_path / "snap.json"
    snap_file.write_text("{}")
    snap = _make_snap([_make_result("stack-a", 2)])

    with patch("stackwatch.budget_cli.Snapshot.load", return_value=snap):
        result = runner.invoke(budget_group, [
            "check", str(snap_file),
            "--cost-per-resource", "10",
            "--monthly-budget", "1000",
            "--json",
        ])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["drifted_resource_count"] == 2
    assert data["estimated_cost"] == 20.0
    assert data["over_budget"] is False


def test_check_invalid_config_exits_with_code_2(runner, tmp_path):
    snap_file = tmp_path / "snap.json"
    snap_file.write_text("{}")

    result = runner.invoke(budget_group, [
        "check", str(snap_file),
        "--monthly-budget", "0",
    ])

    assert result.exit_code == 2


def test_check_missing_snapshot_exits_with_code_2(runner, tmp_path):
    snap_file = tmp_path / "snap.json"
    snap_file.write_text("{}")

    with patch("stackwatch.budget_cli.Snapshot.load", return_value=None):
        result = runner.invoke(budget_group, [
            "check", str(snap_file),
        ])

    assert result.exit_code == 2
