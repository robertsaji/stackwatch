"""Tests for stackwatch.alert_manager."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.alert_manager import AlertManager, AlertManagerConfig
from stackwatch.drift import DriftResult, DriftedResource


def _make_result(stack: str, drifted: bool = True) -> DriftResult:
    resources = [
        DriftedResource(logical_id="Bucket", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=[])
    ] if drifted else []
    return DriftResult(stack_name=stack, has_drift=drifted, drifted_resources=resources)


@pytest.fixture()
def cfg(tmp_path: Path) -> AlertManagerConfig:
    return AlertManagerConfig(
        cooldown_seconds=60.0,
        store_path=tmp_path / "store.json",
        dry_run=False,
    )


@pytest.fixture()
def detector() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def notifier() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def manager(detector: MagicMock, notifier: MagicMock, cfg: AlertManagerConfig) -> AlertManager:
    return AlertManager(detector=detector, notifiers=[notifier], config=cfg)


def test_run_returns_all_results(manager: AlertManager, detector: MagicMock) -> None:
    results = [_make_result("stack-a"), _make_result("stack-b", drifted=False)]
    detector.detect_all.return_value = results
    returned = manager.run(["stack-a", "stack-b"])
    assert returned == results


def test_run_sends_alert_for_drifted_stack(manager: AlertManager, detector: MagicMock, notifier: MagicMock) -> None:
    detector.detect_all.return_value = [_make_result("stack-a")]
    manager.run(["stack-a"])
    notifier.send.assert_called_once()


def test_run_skips_alert_for_in_sync_stack(manager: AlertManager, detector: MagicMock, notifier: MagicMock) -> None:
    detector.detect_all.return_value = [_make_result("stack-a", drifted=False)]
    manager.run(["stack-a"])
    notifier.send.assert_not_called()


def test_run_suppresses_duplicate_alert(manager: AlertManager, detector: MagicMock, notifier: MagicMock) -> None:
    result = _make_result("stack-a")
    detector.detect_all.return_value = [result]
    manager.run(["stack-a"])
    manager.run(["stack-a"])
    assert notifier.send.call_count == 1


def test_dry_run_does_not_send_or_record(manager: AlertManager, detector: MagicMock, notifier: MagicMock) -> None:
    manager.config.dry_run = True
    detector.detect_all.return_value = [_make_result("stack-a")]
    manager.run(["stack-a"])
    notifier.send.assert_not_called()
    assert manager._store._records == {}


def test_reset_clears_suppression(manager: AlertManager, detector: MagicMock, notifier: MagicMock) -> None:
    result = _make_result("stack-a")
    detector.detect_all.return_value = [result]
    manager.run(["stack-a"])
    manager.reset("stack-a")
    manager.run(["stack-a"])
    assert notifier.send.call_count == 2


def test_reset_all_clears_all_stacks(manager: AlertManager, detector: MagicMock, notifier: MagicMock) -> None:
    detector.detect_all.return_value = [_make_result("stack-a"), _make_result("stack-b")]
    manager.run(["stack-a", "stack-b"])
    manager.reset()
    assert manager._store._records == {}
