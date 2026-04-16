"""Tests for stackwatch.suppression."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from stackwatch.suppression import SuppressionRule, SuppressionStore, SuppressionError
from stackwatch.drift import DriftResult


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "suppressions.json"


@pytest.fixture()
def store(store_path: Path) -> SuppressionStore:
    s = SuppressionStore(path=store_path)
    s.load()
    return s


def _make_result(stack_name: str, drifted: bool = True) -> DriftResult:
    from stackwatch.drift import DriftedResource
    resources = [
        DriftedResource(logical_id="R", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected="{}", actual="{}")
    ] if drifted else []
    return DriftResult(stack_name=stack_name, drift_status="DRIFTED" if drifted else "IN_SYNC", drifted_resources=resources)


def test_load_returns_empty_when_no_file(store: SuppressionStore):
    assert store.active_rules() == []


def test_add_and_active_rules(store: SuppressionStore):
    rule = SuppressionRule(stack_name="my-stack", reason="planned")
    store.add(rule)
    assert len(store.active_rules()) == 1
    assert store.active_rules()[0].stack_name == "my-stack"


def test_save_creates_file(store: SuppressionStore, store_path: Path):
    store.add(SuppressionRule(stack_name="s", reason="r"))
    assert store_path.exists()


def test_remove_existing_rule(store: SuppressionStore):
    store.add(SuppressionRule(stack_name="s", reason="r"))
    removed = store.remove("s")
    assert removed is True
    assert store.active_rules() == []


def test_remove_nonexistent_rule(store: SuppressionStore):
    removed = store.remove("ghost")
    assert removed is False


def test_is_suppressed_returns_true(store: SuppressionStore):
    store.add(SuppressionRule(stack_name="my-stack", reason="ok"))
    result = _make_result("my-stack")
    assert store.is_suppressed(result) is True


def test_is_suppressed_returns_false_for_other_stack(store: SuppressionStore):
    store.add(SuppressionRule(stack_name="other", reason="ok"))
    result = _make_result("my-stack")
    assert store.is_suppressed(result) is False


def test_expired_rule_not_suppressed(store: SuppressionStore):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    store.add(SuppressionRule(stack_name="s", reason="r", expires_at=past))
    result = _make_result("s")
    assert store.is_suppressed(result) is False


def test_future_expiry_still_suppressed(store: SuppressionStore):
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    store.add(SuppressionRule(stack_name="s", reason="r", expires_at=future))
    result = _make_result("s")
    assert store.is_suppressed(result) is True


def test_add_replaces_existing_rule(store: SuppressionStore):
    store.add(SuppressionRule(stack_name="s", reason="old"))
    store.add(SuppressionRule(stack_name="s", reason="new"))
    rules = store.active_rules()
    assert len(rules) == 1
    assert rules[0].reason == "new"


def test_load_raises_on_corrupt_file(store_path: Path):
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text("not json")
    s = SuppressionStore(path=store_path)
    with pytest.raises(SuppressionError):
        s.load()
