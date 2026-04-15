"""Tests for stackwatch.alerting."""
import json
import time
from pathlib import Path

import pytest

from stackwatch.alerting import AlertError, AlertRecord, AlertStore, _fingerprint
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "alerts" / "store.json"


@pytest.fixture()
def store(store_path: Path) -> AlertStore:
    return AlertStore(path=store_path, cooldown_seconds=60.0)


def _make_result(stack: str, drifted: bool = True) -> DriftResult:
    resources = [
        DriftedResource(logical_id="Bucket", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=[])
    ] if drifted else []
    return DriftResult(stack_name=stack, has_drift=drifted, drifted_resources=resources)


def test_should_alert_returns_false_for_in_sync(store: AlertStore) -> None:
    result = _make_result("my-stack", drifted=False)
    assert store.should_alert(result) is False


def test_should_alert_returns_true_for_new_drift(store: AlertStore) -> None:
    result = _make_result("my-stack")
    assert store.should_alert(result) is True


def test_should_alert_suppressed_within_cooldown(store: AlertStore) -> None:
    result = _make_result("my-stack")
    store.record_alert(result)
    assert store.should_alert(result) is False


def test_should_alert_after_cooldown_expires(store: AlertStore, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _make_result("my-stack")
    store.record_alert(result)
    monkeypatch.setattr(time, "time", lambda: time.time() + 120.0)
    assert store.should_alert(result) is True


def test_should_alert_when_fingerprint_changes(store: AlertStore) -> None:
    result1 = _make_result("my-stack")
    store.record_alert(result1)
    result2 = DriftResult(
        stack_name="my-stack",
        has_drift=True,
        drifted_resources=[
            DriftedResource(logical_id="Queue", resource_type="AWS::SQS::Queue", status="MODIFIED", properties=[])
        ],
    )
    assert store.should_alert(result2) is True


def test_record_alert_persists_to_disk(store: AlertStore, store_path: Path) -> None:
    result = _make_result("my-stack")
    store.record_alert(result)
    assert store_path.exists()
    data = json.loads(store_path.read_text())
    assert "my-stack" in data


def test_record_alert_increments_send_count(store: AlertStore, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _make_result("my-stack")
    store.record_alert(result)
    monkeypatch.setattr(time, "time", lambda: time.time() + 120.0)
    store.record_alert(result)
    assert store._records["my-stack"].send_count == 2


def test_clear_removes_specific_stack(store: AlertStore) -> None:
    store.record_alert(_make_result("stack-a"))
    store.record_alert(_make_result("stack-b"))
    store.clear("stack-a")
    assert "stack-a" not in store._records
    assert "stack-b" in store._records


def test_clear_all_removes_everything(store: AlertStore) -> None:
    store.record_alert(_make_result("stack-a"))
    store.record_alert(_make_result("stack-b"))
    store.clear()
    assert store._records == {}


def test_load_raises_alert_error_on_corrupt_file(store_path: Path) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text("not json{{{")
    with pytest.raises(AlertError):
        AlertStore(path=store_path)


def test_fingerprint_stable_across_calls() -> None:
    result = _make_result("my-stack")
    assert _fingerprint(result) == _fingerprint(result)
