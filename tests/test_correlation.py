"""Tests for stackwatch.correlation."""
from __future__ import annotations
import pytest
from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.correlation import (
    build_correlation_report,
    render_correlation_text,
    CorrelationReport,
)


def _make_resource(resource_type: str) -> DriftedResource:
    return DriftedResource(
        logical_id="res",
        resource_type=resource_type,
        drift_status="MODIFIED",
        expected_properties="{}",
        actual_properties="{}",
    )


def _make_result(stack_name: str, types: list[str], drifted: bool = True) -> DriftResult:
    resources = [_make_resource(t) for t in types] if drifted else []
    return DriftResult(stack_name=stack_name, drift_status="DRIFTED" if drifted else "IN_SYNC", drifted_resources=resources)


def test_build_correlation_empty():
    report = build_correlation_report([])
    assert report.groups == []
    assert not report.has_correlations


def test_build_correlation_single_stack():
    results = [_make_result("stack-a", ["AWS::S3::Bucket"])]
    report = build_correlation_report(results)
    assert len(report.groups) == 1
    assert report.groups[0].count == 1
    assert not report.has_correlations


def test_build_correlation_shared_type():
    results = [
        _make_result("stack-a", ["AWS::S3::Bucket"]),
        _make_result("stack-b", ["AWS::S3::Bucket"]),
    ]
    report = build_correlation_report(results)
    assert report.has_correlations
    group = report.groups[0]
    assert group.resource_type == "AWS::S3::Bucket"
    assert group.count == 2
    assert "stack-a" in group.stacks
    assert "stack-b" in group.stacks


def test_in_sync_stacks_excluded():
    results = [
        _make_result("stack-a", ["AWS::IAM::Role"], drifted=False),
        _make_result("stack-b", ["AWS::IAM::Role"]),
    ]
    report = build_correlation_report(results)
    assert len(report.groups) == 1
    assert report.groups[0].stacks == ["stack-b"]


def test_top_limits_results():
    results = [
        _make_result(f"stack-{i}", ["AWS::S3::Bucket", "AWS::EC2::Instance"])
        for i in range(3)
    ]
    report = build_correlation_report(results)
    top = report.top(1)
    assert len(top) == 1


def test_render_text_no_correlations():
    report = CorrelationReport(groups=[])
    text = render_correlation_text(report)
    assert "No correlated drift" in text


def test_render_text_shows_type():
    results = [
        _make_result("stack-a", ["AWS::S3::Bucket"]),
        _make_result("stack-b", ["AWS::S3::Bucket"]),
    ]
    report = build_correlation_report(results)
    text = render_correlation_text(report)
    assert "AWS::S3::Bucket" in text
