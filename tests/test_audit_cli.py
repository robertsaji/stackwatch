"""Tests for stackwatch.audit_cli."""
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from stackwatch.audit_cli import audit_group
from stackwatch.audit import AuditLog
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    return tmp_path / "audit.json"


def _make_result(name: str, drifted: bool = False) -> DriftResult:
    resources = [
        DriftedResource(logical_id="R", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})
    ] if drifted else []
    return DriftResult(stack_name=name, status="DRIFTED" if drifted else "IN_SYNC", drifted_resources=resources)


def test_list_empty(runner: CliRunner, log_file: Path):
    result = runner.invoke(audit_group, ["list", "--log-file", str(log_file)])
    assert result.exit_code == 0
    assert "No audit entries" in result.output


def test_list_shows_entries(runner: CliRunner, log_file: Path):
    log = AuditLog(log_file)
    log.record(_make_result("stack-a", drifted=True))
    result = runner.invoke(audit_group, ["list", "--log-file", str(log_file)])
    assert result.exit_code == 0
    assert "stack-a" in result.output
    assert "DRIFTED" in result.output


def test_list_filtered_by_stack(runner: CliRunner, log_file: Path):
    log = AuditLog(log_file)
    log.record(_make_result("stack-a"))
    log.record(_make_result("stack-b", drifted=True))
    result = runner.invoke(audit_group, ["list", "--stack", "stack-b", "--log-file", str(log_file)])
    assert "stack-b" in result.output
    assert "stack-a" not in result.output


def test_clear_removes_entries(runner: CliRunner, log_file: Path):
    log = AuditLog(log_file)
    log.record(_make_result("stack-a"))
    result = runner.invoke(audit_group, ["clear", "--log-file", str(log_file)], input="y\n")
    assert result.exit_code == 0
    assert "cleared" in result.output
    log2 = AuditLog(log_file)
    assert log2.entries() == []
