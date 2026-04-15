"""Tests for stackwatch.reporter."""
import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.reporter import build_report, render_html, render_text


@pytest.fixture()
def drifted_resource():
    return DriftedResource(
        logical_id="MyBucket",
        resource_type="AWS::S3::Bucket",
        drift_status="MODIFIED",
    )


@pytest.fixture()
def drifted_result(drifted_resource):
    return DriftResult(
        stack_name="prod-stack",
        drifted=True,
        drifted_resources=[drifted_resource],
    )


@pytest.fixture()
def in_sync_result():
    return DriftResult(stack_name="dev-stack", drifted=False, drifted_resources=[])


def test_build_report_counts(drifted_result, in_sync_result):
    report = build_report([drifted_result, in_sync_result])
    assert report.total_stacks == 2
    assert report.drifted_stacks == 1
    assert report.has_drift is True


def test_build_report_no_drift(in_sync_result):
    report = build_report([in_sync_result])
    assert report.has_drift is False
    assert report.drifted_stacks == 0


def test_build_report_empty():
    report = build_report([])
    assert report.total_stacks == 0
    assert report.drifted_stacks == 0


def test_render_text_contains_stack_name(drifted_result, in_sync_result):
    report = build_report([drifted_result, in_sync_result])
    text = render_text(report)
    assert "prod-stack" in text
    assert "dev-stack" in text


def test_render_text_shows_drifted_status(drifted_result):
    report = build_report([drifted_result])
    text = render_text(report)
    assert "DRIFTED" in text
    assert "MyBucket" in text


def test_render_text_shows_in_sync(in_sync_result):
    report = build_report([in_sync_result])
    text = render_text(report)
    assert "IN_SYNC" in text


def test_render_html_contains_table(drifted_result, in_sync_result):
    report = build_report([drifted_result, in_sync_result])
    html = render_html(report)
    assert "<table" in html
    assert "prod-stack" in html
    assert "dev-stack" in html


def test_render_html_drifted_color(drifted_result):
    report = build_report([drifted_result])
    html = render_html(report)
    assert "#c0392b" in html


def test_render_html_in_sync_color(in_sync_result):
    report = build_report([in_sync_result])
    html = render_html(report)
    assert "#27ae60" in html
