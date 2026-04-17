"""Tests for stackwatch.severity."""
import pytest
from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.severity import (
    SeverityLevel,
    SeverityResult,
    classify,
    classify_all,
    render_severity_text,
)


def _make_resource(logical_id: str, drifted: bool) -> DriftedResource:
    return DriftedResource(logical_id=logical_id, resource_type="AWS::S3::Bucket", drifted=drifted)


def _make_result(name: str, drifted_count: int, total: int) -> DriftResult:
    resources = [_make_resource(f"R{i}", i < drifted_count) for i in range(total)]
    return DriftResult(stack_name=name, resources=resources)


def test_classify_no_drift_is_low():
    result = _make_result("clean", 0, 4)
    sr = classify(result)
    assert sr.level == SeverityLevel.LOW
    assert sr.drifted_count == 0


def test_classify_low_drift():
    result = _make_result("s1", 1, 8)  # 12.5%
    sr = classify(result)
    assert sr.level == SeverityLevel.LOW


def test_classify_medium_drift():
    result = _make_result("s2", 2, 6)  # 33%
    sr = classify(result)
    assert sr.level == SeverityLevel.MEDIUM


def test_classify_high_drift():
    result = _make_result("s3", 3, 5)  # 60%
    sr = classify(result)
    assert sr.level == SeverityLevel.HIGH


def test_classify_critical_drift():
    result = _make_result("s4", 4, 4)  # 100%
    sr = classify(result)
    assert sr.level == SeverityLevel.CRITICAL
    assert sr.drifted_count == 4


def test_classify_all_returns_one_per_result():
    results = [_make_result(f"stack-{i}", i, 4) for i in range(3)]
    severity_results = classify_all(results)
    assert len(severity_results) == 3


def test_render_text_contains_stack_name():
    sr = SeverityResult(stack_name="my-stack", level=SeverityLevel.HIGH, drifted_count=2, total_count=4)
    text = render_severity_text([sr])
    assert "my-stack" in text
    assert "HIGH" in text


def test_render_text_empty():
    text = render_severity_text([])
    assert "No results" in text
