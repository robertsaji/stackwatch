"""Tests for stackwatch.baseline module."""
import json
import pytest
from pathlib import Path

from stackwatch.baseline import DriftBaseline, BaselineError
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture
def baseline_path(tmp_path: Path) -> Path:
    return tmp_path / "baseline" / "drift.json"


@pytest.fixture
def baseline(baseline_path: Path) -> DriftBaseline:
    return DriftBaseline(baseline_path)


def _make_result(name: str, drifted: bool, resource_ids=()) -> DriftResult:
    resources = [
        DriftedResource(logical_id=rid, resource_type="AWS::S3::Bucket", drift_status="MODIFIED")
        for rid in resource_ids
    ]
    return DriftResult(stack_name=name, drifted=drifted, resources=resources)


def test_load_returns_empty_when_no_file(baseline: DriftBaseline) -> None:
    assert baseline.load() == {}


def test_save_creates_file(baseline: DriftBaseline, baseline_path: Path) -> None:
    result = _make_result("my-stack", True, ["BucketA"])
    baseline.save([result])
    assert baseline_path.exists()


def test_save_and_load_round_trip(baseline: DriftBaseline) -> None:
    result = _make_result("stack-1", True, ["Res1", "Res2"])
    baseline.save([result])
    loaded = baseline.load()
    assert "stack-1" in loaded
    assert loaded["stack-1"].drifted is True
    assert {r.logical_id for r in loaded["stack-1"].resources} == {"Res1", "Res2"}


def test_save_multiple_stacks(baseline: DriftBaseline) -> None:
    results = [
        _make_result("stack-a", True, ["R1"]),
        _make_result("stack-b", False, []),
    ]
    baseline.save(results)
    loaded = baseline.load()
    assert set(loaded.keys()) == {"stack-a", "stack-b"}


def test_new_drift_returns_unknown_stacks(baseline: DriftBaseline) -> None:
    """A drifted stack not in the baseline should be returned."""
    result = _make_result("new-stack", True, ["R1"])
    new = baseline.new_drift([result])
    assert len(new) == 1
    assert new[0].stack_name == "new-stack"


def test_new_drift_skips_in_sync(baseline: DriftBaseline) -> None:
    result = _make_result("ok-stack", False, [])
    new = baseline.new_drift([result])
    assert new == []


def test_new_drift_skips_unchanged_drift(baseline: DriftBaseline) -> None:
    """If the same resources are drifted as in the baseline, no alert."""
    result = _make_result("stack-x", True, ["R1"])
    baseline.save([result])
    new = baseline.new_drift([result])
    assert new == []


def test_new_drift_detects_additional_resources(baseline: DriftBaseline) -> None:
    """New drifted resources beyond the baseline should trigger an alert."""
    original = _make_result("stack-x", True, ["R1"])
    baseline.save([original])
    updated = _make_result("stack-x", True, ["R1", "R2"])
    new = baseline.new_drift([updated])
    assert len(new) == 1
    assert new[0].stack_name == "stack-x"


def test_load_raises_on_corrupt_file(baseline: DriftBaseline, baseline_path: Path) -> None:
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text("not valid json")
    with pytest.raises(BaselineError):
        baseline.load()
