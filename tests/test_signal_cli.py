"""Tests for stackwatch.signal_cli."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from stackwatch.signal_cli import signal_group
from stackwatch.signal import SignalReport, StackSignal
from stackwatch.snapshot import Snapshot
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _make_resource(status: str = "MODIFIED") -> DriftedResource:
    return DriftedResource(
        logical_id="R",
        resource_type="AWS::EC2::Instance",
        drift_status=status,
        expected_properties="{}",
        actual_properties="{}",
    )


def _make_snap(drifted: bool = True) -> Snapshot:
    result = DriftResult(
        stack_name="test-stack",
        drift_status="DRIFTED" if drifted else "IN_SYNC",
        resources=[_make_resource()] if drifted else [],
    )
    snap = MagicMock(spec=Snapshot)
    snap.results = {"test-stack": result}
    return snap


def _patch(snap: Snapshot):
    return patch("stackwatch.signal_cli.Snapshot.load", return_value=snap)


def test_show_command_exits_zero(runner, tmp_path):
    snap = _make_snap(drifted=True)
    with _patch(snap):
        result = runner.invoke(signal_group, ["show", str(tmp_path / "snap.json")])
    assert result.exit_code == 0


def test_show_command_contains_stack_name(runner, tmp_path):
    snap = _make_snap(drifted=True)
    with _patch(snap):
        result = runner.invoke(signal_group, ["show", str(tmp_path / "snap.json")])
    assert "test-stack" in result.output


def test_show_command_no_signals_above_threshold(runner, tmp_path):
    snap = _make_snap(drifted=False)
    with _patch(snap):
        result = runner.invoke(
            signal_group, ["show", str(tmp_path / "snap.json"), "--min-score", "999"]
        )
    assert "No signals" in result.output
    assert result.exit_code == 0


def test_text_command_exits_zero(runner, tmp_path):
    snap = _make_snap(drifted=True)
    with _patch(snap):
        result = runner.invoke(signal_group, ["text", str(tmp_path / "snap.json")])
    assert result.exit_code == 0
    assert "Signal Report" in result.output


def test_json_command_returns_valid_json(runner, tmp_path):
    import json
    snap = _make_snap(drifted=True)
    with _patch(snap):
        result = runner.invoke(signal_group, ["json", str(tmp_path / "snap.json")])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["stack_name"] == "test-stack"


def test_show_missing_snapshot_exits_nonzero(runner, tmp_path):
    with patch("stackwatch.signal_cli.Snapshot.load", return_value=None):
        result = runner.invoke(signal_group, ["show", str(tmp_path / "missing.json")])
    assert result.exit_code != 0
