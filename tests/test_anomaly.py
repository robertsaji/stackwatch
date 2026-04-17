"""Tests for stackwatch.anomaly."""
import pytest

from stackwatch.anomaly import AnomalyConfig, detect_anomaly, detect_anomalies
from stackwatch.trend import TrendPoint
from stackwatch.drift import DriftResult, DriftedResource


def _make_result(name: str, drifted: bool) -> DriftResult:
    resources = [
        DriftedResource(logical_id="R1", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=[])
    ] if drifted else []
    return DriftResult(stack_name=name, drifted_resources=resources)


def _points(rates):
    return [TrendPoint(timestamp="2024-01-01", drift_rate=r, total=10, drifted=int(r * 10)) for r in rates]


def test_invalid_min_points_raises():
    with pytest.raises(ValueError, match="min_points"):
        AnomalyConfig(min_points=0)


def test_invalid_threshold_raises():
    with pytest.raises(ValueError, match="z_score_threshold"):
        AnomalyConfig(z_score_threshold=0.0)


def test_not_enough_history_returns_no_anomaly():
    result = _make_result("my-stack", True)
    anomaly = detect_anomaly("my-stack", _points([0.1, 0.2]), result)
    assert anomaly.is_anomaly is False
    assert anomaly.z_score == 0.0


def test_no_drift_within_normal_range():
    result = _make_result("my-stack", False)
    history = _points([0.0, 0.0, 0.1, 0.0, 0.0])
    anomaly = detect_anomaly("my-stack", history, result)
    assert anomaly.is_anomaly is False
    assert anomaly.current_rate == 0.0


def test_sudden_drift_flagged_as_anomaly():
    result = _make_result("my-stack", True)
    # history is always 0 drift, sudden 1.0 should be anomalous
    history = _points([0.0, 0.0, 0.0, 0.0, 0.0])
    anomaly = detect_anomaly("my-stack", history, result, AnomalyConfig(z_score_threshold=1.0))
    assert anomaly.is_anomaly is True
    assert anomaly.current_rate == 1.0


def test_zero_std_no_anomaly_when_matches_mean():
    result = _make_result("my-stack", False)
    history = _points([0.0, 0.0, 0.0])
    anomaly = detect_anomaly("my-stack", history, result)
    assert anomaly.z_score == 0.0
    assert anomaly.is_anomaly is False


def test_detect_anomalies_batch():
    results = [_make_result("a", True), _make_result("b", False)]
    history_map = {
        "a": _points([0.0, 0.0, 0.0, 0.0, 0.0]),
        "b": _points([0.0, 0.0, 0.0]),
    }
    anomalies = detect_anomalies(results, history_map, AnomalyConfig(z_score_threshold=1.0))
    assert len(anomalies) == 2
    assert anomalies[0].stack_name == "a"
    assert anomalies[0].is_anomaly is True
    assert anomalies[1].is_anomaly is False


def test_detect_anomalies_missing_history():
    results = [_make_result("x", True)]
    anomalies = detect_anomalies(results, {})
    assert anomalies[0].is_anomaly is False
