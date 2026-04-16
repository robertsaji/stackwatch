"""Tests for stackwatch.remediation."""
import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.remediation import (
    build_remediation_report,
    render_remediation_text,
    RemediationReport,
)


@pytest.fixture
def drifted_resource() -> DriftedResource:
    return DriftedResource(
        resource_id="MyBucket",
        resource_type="AWS::S3::Bucket",
        drift_status="MODIFIED",
    )


@pytest.fixture
def drifted_result(drifted_resource) -> DriftResult:
    return DriftResult(
        stack_name="my-stack",
        drift_status="DRIFTED",
        drifted_resources=[drifted_resource],
    )


@pytest.fixture
def in_sync_result() -> DriftResult:
    return DriftResult(
        stack_name="clean-stack",
        drift_status="IN_SYNC",
        drifted_resources=[],
    )


def test_build_report_has_hints_for_drifted(drifted_result):
    report = build_remediation_report(drifted_result)
    assert report.has_hints
    assert len(report.hints) == 1
    assert report.hints[0].resource_id == "MyBucket"


def test_build_report_no_hints_for_in_sync(in_sync_result):
    report = build_remediation_report(in_sync_result)
    assert not report.has_hints
    assert report.hints == []


def test_hint_action_for_modified(drifted_result):
    report = build_remediation_report(drifted_result)
    assert report.hints[0].action == "update"


def test_hint_action_for_deleted():
    resource = DriftedResource(
        resource_id="MyFunc",
        resource_type="AWS::Lambda::Function",
        drift_status="DELETED",
    )
    result = DriftResult(stack_name="s", drift_status="DRIFTED", drifted_resources=[resource])
    report = build_remediation_report(result)
    assert report.hints[0].action == "recreate"


def test_render_text_no_hints(in_sync_result):
    report = build_remediation_report(in_sync_result)
    text = render_remediation_text(report)
    assert "no remediation needed" in text


def test_render_text_with_hints(drifted_result):
    report = build_remediation_report(drifted_result)
    text = render_remediation_text(report)
    assert "MyBucket" in text
    assert "UPDATE" in text
    assert "my-stack" in text


def test_stack_name_in_report(drifted_result):
    report = build_remediation_report(drifted_result)
    assert report.stack_name == "my-stack"
