"""Tests for stackwatch.cli."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from stackwatch.cli import cli


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def _patch_deps():
    """Patch heavy AWS/network dependencies for all CLI tests."""
    with (
        patch("stackwatch.cli.load_config") as mock_cfg,
        patch("stackwatch.cli.DriftDetector") as mock_detector_cls,
        patch("stackwatch.cli.SlackNotifier") as mock_notifier_cls,
        patch("stackwatch.cli.DriftScheduler") as mock_scheduler_cls,
    ):
        cfg = MagicMock()
        cfg.interval_seconds = 300
        mock_cfg.return_value = cfg

        detector = MagicMock()
        detector.detect_all.return_value = []
        mock_detector_cls.return_value = detector

        notifier = MagicMock()
        mock_notifier_cls.return_value = notifier

        scheduler = MagicMock()
        mock_scheduler_cls.return_value = scheduler

        yield {
            "config": mock_cfg,
            "detector": detector,
            "notifier": notifier,
            "scheduler": scheduler,
            "scheduler_cls": mock_scheduler_cls,
        }


def test_run_once_calls_detect_all(runner, _patch_deps):
    result = runner.invoke(cli, ["run", "--once"])
    assert result.exit_code == 0
    _patch_deps["detector"].detect_all.assert_called_once()


def test_run_once_calls_notifier_for_each_result(runner, _patch_deps):
    drift = MagicMock()
    _patch_deps["detector"].detect_all.return_value = [drift, drift]
    result = runner.invoke(cli, ["run", "--once"])
    assert result.exit_code == 0
    assert _patch_deps["notifier"].send.call_count == 2


def test_run_starts_scheduler(runner, _patch_deps):
    result = runner.invoke(cli, ["run"])
    assert result.exit_code == 0
    _patch_deps["scheduler_cls"].assert_called_once()
    _patch_deps["scheduler"].start.assert_called_once()


def test_run_passes_interval_to_scheduler(runner, _patch_deps):
    runner.invoke(cli, ["run"])
    _, kwargs = _patch_deps["scheduler_cls"].call_args
    assert kwargs["interval_seconds"] == 300
