"""Tests for stackwatch.sla_cli."""
import pytest
from click.testing import CliRunner
from pathlib import Path
from datetime import datetime, timedelta
from stackwatch.sla_cli import sla_group
from stackwatch.sla import SLATracker, SLAConfig


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def store_file(tmp_path: Path) -> str:
    return str(tmp_path / "sla.json")


def test_status_empty(runner, store_file):
    result = runner.invoke(sla_group, ["status", "--store", store_file])
    assert result.exit_code == 0
    assert "No drifted" in result.output


def test_status_shows_ok(runner, store_file):
    tracker = SLATracker(path=Path(store_file), config=SLAConfig(max_drift_hours=24))
    tracker.record_drift("my-stack", at=datetime.utcnow())
    result = runner.invoke(sla_group, ["status", "--store", store_file])
    assert result.exit_code == 0
    assert "my-stack" in result.output


def test_clear_command(runner, store_file):
    tracker = SLATracker(path=Path(store_file))
    tracker.record_drift("stack-x")
    result = runner.invoke(sla_group, ["clear", "stack-x", "--store", store_file])
    assert result.exit_code == 0
    assert "Cleared" in result.output
    assert tracker.status("stack-x") is None
