"""Tests for stackwatch.severity_cli."""
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from stackwatch.severity_cli import severity_group
from stackwatch.drift import DriftResult, DriftedResource


def _make_result(name: str, drifted: bool) -> DriftResult:
    resource = DriftedResource(logical_id="Res", resource_type="AWS::EC2::Instance", drifted=drifted)
    return DriftResult(stack_name=name, resources=[resource])


@pytest.fixture
def runner():
    return CliRunner()


import pytest


@patch("stackwatch.severity_cli.DriftDetector")
@patch("stackwatch.severity_cli.load_config")
def test_check_exits_zero_when_no_high_severity(mock_cfg, mock_detector_cls, runner):
    mock_cfg.return_value = MagicMock()
    inst = MagicMock()
    inst.detect_all.return_value = [_make_result("clean", False)]
    mock_detector_cls.return_value = inst

    result = runner.invoke(severity_group, ["check"])
    assert result.exit_code == 0
    assert "clean" in result.output


@patch("stackwatch.severity_cli.DriftDetector")
@patch("stackwatch.severity_cli.load_config")
def test_check_exits_nonzero_for_critical(mock_cfg, mock_detector_cls, runner):
    mock_cfg.return_value = MagicMock()
    inst = MagicMock()
    resources = [DriftedResource(logical_id=f"R{i}", resource_type="AWS::S3::Bucket", drifted=True) for i in range(4)]
    inst.detect_all.return_value = [DriftResult(stack_name="bad-stack", resources=resources)]
    mock_detector_cls.return_value = inst

    result = runner.invoke(severity_group, ["check"])
    assert result.exit_code != 0


@patch("stackwatch.severity_cli.DriftDetector")
@patch("stackwatch.severity_cli.load_config")
def test_check_min_level_filters(mock_cfg, mock_detector_cls, runner):
    mock_cfg.return_value = MagicMock()
    inst = MagicMock()
    inst.detect_all.return_value = [_make_result("ok", False)]
    mock_detector_cls.return_value = inst

    result = runner.invoke(severity_group, ["check", "--min-level", "high"])
    assert result.exit_code == 0
    assert "ok" not in result.output or "LOW" not in result.output
