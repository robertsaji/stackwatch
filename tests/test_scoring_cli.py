"""Tests for stackwatch.scoring_cli."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.scoring_cli import scoring_group


def _make_resource(name: str) -> DriftedResource:
    return DriftedResource(
        logical_id=name,
        resource_type="AWS::EC2::Instance",
        drift_status="MODIFIED",
        expected={},
        actual={},
    )


def _make_result(name: str, n: int) -> DriftResult:
    return DriftResult(
        stack_name=name,
        status="DRIFTED" if n else "IN_SYNC",
        drifted_resources=[_make_resource(f"R{i}") for i in range(n)],
    )


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _patch(results):
    return patch(
        "stackwatch.scoring_cli.DriftDetector",
        return_value=MagicMock(detect_all=MagicMock(return_value=results)),
    )


def test_check_no_drift_exits_zero(runner):
    with _patch([_make_result("clean", 0)]):
        result = runner.invoke(scoring_group, ["check"])
    assert result.exit_code == 0


def test_check_shows_stack_name(runner):
    with _patch([_make_result("my-stack", 2)]):
        result = runner.invoke(scoring_group, ["check"])
    assert "my-stack" in result.output


def test_check_min_score_filters(runner):
    with _patch([_make_result("low", 0), _make_result("high", 10)]):
        result = runner.invoke(scoring_group, ["check", "--min-score", "50"])
    # low-drift stack should be filtered out; high-drift stack should appear
    assert "high" in result.output


def test_check_exit_nonzero_on_critical(runner):
    with _patch([_make_result("critical-stack", 20)]):
        result = runner.invoke(scoring_group, ["check", "--exit-nonzero"])
    assert result.exit_code == 1


def test_check_no_exit_nonzero_without_flag(runner):
    with _patch([_make_result("critical-stack", 20)]):
        result = runner.invoke(scoring_group, ["check"])
    assert result.exit_code == 0


def test_check_empty_results(runner):
    with _patch([]):
        result = runner.invoke(scoring_group, ["check"])
    assert result.exit_code == 0
    assert "No stacks" in result.output
