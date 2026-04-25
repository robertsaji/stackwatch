"""Tests for stackwatch.compliance."""
import pytest

from stackwatch.compliance import (
    ComplianceConfig,
    ComplianceError,
    check_compliance,
    render_compliance_text,
)
from stackwatch.drift import DriftResult, DriftedResource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(stack_name: str, drifted: bool) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="R", resource_type="AWS::S3::Bucket", status="MODIFIED", properties={})]
        if drifted
        else []
    )
    return DriftResult(stack_name=stack_name, resources=resources)


# ---------------------------------------------------------------------------
# ComplianceConfig validation
# ---------------------------------------------------------------------------

def test_invalid_max_drifted_pct_raises():
    with pytest.raises(ComplianceError):
        ComplianceConfig(max_drifted_pct=-1.0)


def test_max_drifted_pct_above_100_raises():
    with pytest.raises(ComplianceError):
        ComplianceConfig(max_drifted_pct=101.0)


def test_valid_config_does_not_raise():
    cfg = ComplianceConfig(max_drifted_pct=50.0)
    assert cfg.max_drifted_pct == 50.0


# ---------------------------------------------------------------------------
# check_compliance
# ---------------------------------------------------------------------------

def test_no_drift_is_compliant():
    results = [_make_result("stack-a", False), _make_result("stack-b", False)]
    outcome = check_compliance(results)
    assert outcome.is_compliant
    assert outcome.drifted_stacks == 0
    assert outcome.violations == []


def test_drift_with_zero_tolerance_is_non_compliant():
    results = [_make_result("stack-a", True), _make_result("stack-b", False)]
    outcome = check_compliance(results, ComplianceConfig(max_drifted_pct=0.0))
    assert not outcome.is_compliant
    assert outcome.drifted_stacks == 1
    assert len(outcome.violations) == 1
    assert outcome.violations[0].stack_name == "stack-a"


def test_drift_within_allowed_pct_is_compliant():
    # 1 out of 4 drifted = 25 %, allow 50 %
    results = [
        _make_result("s1", True),
        _make_result("s2", False),
        _make_result("s3", False),
        _make_result("s4", False),
    ]
    outcome = check_compliance(results, ComplianceConfig(max_drifted_pct=50.0))
    assert outcome.is_compliant
    assert outcome.violations == []


def test_exempt_stacks_excluded_from_evaluation():
    results = [_make_result("stack-exempt", True), _make_result("stack-ok", False)]
    cfg = ComplianceConfig(exempt_stacks=["stack-exempt"])
    outcome = check_compliance(results, cfg)
    assert outcome.is_compliant
    assert outcome.total_stacks == 1
    assert "stack-exempt" in outcome.exempt_stacks


def test_empty_results_is_compliant():
    outcome = check_compliance([])
    assert outcome.is_compliant
    assert outcome.total_stacks == 0
    assert outcome.drifted_pct == 0.0


# ---------------------------------------------------------------------------
# render_compliance_text
# ---------------------------------------------------------------------------

def test_render_text_contains_status():
    results = [_make_result("stack-a", False)]
    outcome = check_compliance(results)
    text = render_compliance_text(outcome)
    assert "COMPLIANT" in text
    assert "stack-a" not in text  # no violations


def test_render_text_lists_violations():
    results = [_make_result("bad-stack", True)]
    outcome = check_compliance(results, ComplianceConfig(max_drifted_pct=0.0))
    text = render_compliance_text(outcome)
    assert "NON-COMPLIANT" in text
    assert "bad-stack" in text
