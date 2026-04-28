"""Tests for stackwatch.checkpoint_manager."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from stackwatch.checkpoint_manager import CheckpointManager, CheckpointManagerConfig
from stackwatch.drift import DriftResult, DriftedResource


def _make_result(stack_name: str, drifted: bool = False) -> DriftResult:
    resources = []
    if drifted:
        resources = [DriftedResource(logical_id="Res1", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})]
    return DriftResult(stack_name=stack_name, drifted=drifted, resources=resources)


@pytest.fixture()
def cfg(tmp_path: Path) -> CheckpointManagerConfig:
    return CheckpointManagerConfig(checkpoint_path=tmp_path / "cp.json")


@pytest.fixture()
def manager(cfg: CheckpointManagerConfig) -> CheckpointManager:
    return CheckpointManager(cfg)


def test_record_returns_checkpoint(manager: CheckpointManager) -> None:
    results = [_make_result("s1"), _make_result("s2", drifted=True)]
    cp = manager.record(results)
    assert cp.stack_names == ["s1", "s2"]
    assert cp.drifted_stacks == ["s2"]


def test_record_persists_to_disk(manager: CheckpointManager, cfg: CheckpointManagerConfig) -> None:
    manager.record([_make_result("s1")])
    assert cfg.checkpoint_path.exists()


def test_latest_returns_none_before_any_run(manager: CheckpointManager) -> None:
    assert manager.latest() is None


def test_latest_returns_last_checkpoint(manager: CheckpointManager) -> None:
    manager.record([_make_result("s1")])
    cp = manager.latest()
    assert cp is not None
    assert "s1" in cp.stack_names


def test_clear_removes_checkpoint(manager: CheckpointManager, cfg: CheckpointManagerConfig) -> None:
    manager.record([_make_result("s1")])
    manager.clear()
    assert manager.latest() is None


def test_run_id_is_unique(manager: CheckpointManager) -> None:
    cp1 = manager.record([_make_result("s1")])
    cp2 = manager.record([_make_result("s2")])
    assert cp1.run_id != cp2.run_id


def test_extra_metadata_included(tmp_path: Path) -> None:
    cfg = CheckpointManagerConfig(
        checkpoint_path=tmp_path / "cp.json",
        extra_metadata={"region": "us-east-1"},
    )
    mgr = CheckpointManager(cfg)
    cp = mgr.record([_make_result("s1")])
    assert cp.metadata.get("region") == "us-east-1"
