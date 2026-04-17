"""Tests for stackwatch.policy."""
import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.policy import (
    PolicyConfig,
    PolicyError,
    evaluate_policy,
)


def _make_result(name: str, drifted: bool) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="R", resource_type="AWS::S3::Bucket", status="MODIFIED", properties={})]
        if drifted
        else []
    )
    return DriftResult(stack_name=name, drifted_resources=resources)


def test_invalid_max_drifted_stacks_raises():
    with pytest.raises(PolicyError):
        PolicyConfig(max_drifted_stacks=-1)


def test_invalid_max_drift_rate_raises():
    with pytest.raises(PolicyError):
        PolicyConfig(max_drift_rate=1.5)


def test_no_drift_passes_default_policy():
    results = [_make_result("stack-a", False), _make_result("stack-b", False)]
    cfg = PolicyConfig()
    result = evaluate_policy(results, cfg)
    assert result.passed
    assert not result.should_fail


def test_any_drift_fails_default_policy():
    results = [_make_result("stack-a", True), _make_result("stack-b", False)]
    cfg = PolicyConfig()  # max_drifted_stacks=0
    result = evaluate_policy(results, cfg)
    assert not result.passed
    assert result.should_fail


def test_drift_within_allowed_count_passes():
    results = [_make_result("stack-a", True), _make_result("stack-b", False)]
    cfg = PolicyConfig(max_drifted_stacks=1, max_drift_rate=1.0)
    result = evaluate_policy(results, cfg)
    assert result.passed


def test_drift_rate_exceeded_creates_violations():
    results = [
        _make_result("a", True),
        _make_result("b", True),
        _make_result("c", False),
    ]
    cfg = PolicyConfig(max_drift_rate=0.5, max_drifted_stacks=10)
    result = evaluate_policy(results, cfg)
    assert not result.passed
    assert len(result.violations) == 2


def test_warn_only_does_not_fail():
    results = [_make_result("stack-a", True)]
    cfg = PolicyConfig(warn_only=True)
    result = evaluate_policy(results, cfg)
    assert not result.passed
    assert not result.should_fail


def test_render_text_passed():
    result = evaluate_policy([], PolicyConfig())
    assert "passed" in result.render_text()


def test_render_text_violations_contain_stack_name():
    results = [_make_result("my-stack", True)]
    cfg = PolicyConfig()
    result = evaluate_policy(results, cfg)
    text = result.render_text()
    assert "my-stack" in text
    assert "[FAIL]" in text


def test_render_text_warn_only_prefix():
    results = [_make_result("my-stack", True)]
    cfg = PolicyConfig(warn_only=True)
    result = evaluate_policy(results, cfg)
    text = result.render_text()
    assert "[WARN]" in text
