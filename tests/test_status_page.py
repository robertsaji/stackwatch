"""Tests for stackwatch.status_page."""
from datetime import datetime, timezone

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.status_page import (
    StatusPage,
    build_status_page,
    render_status_html,
    render_status_text,
)


@pytest.fixture()
def drifted_resource() -> DriftedResource:
    return DriftedResource(logical_id="MyBucket", resource_type="AWS::S3::Bucket", drift_status="MODIFIED")


@pytest.fixture()
def drifted_result(drifted_resource) -> DriftResult:
    return DriftResult(stack_name="stack-a", has_drift=True, drifted_resources=[drifted_resource])


@pytest.fixture()
def in_sync_result() -> DriftResult:
    return DriftResult(stack_name="stack-b", has_drift=False, drifted_resources=[])


def test_build_status_page_counts(drifted_result, in_sync_result):
    page = build_status_page([drifted_result, in_sync_result])
    assert page.total_stacks == 2
    assert page.drifted_stacks == 1
    assert page.in_sync_stacks == 1


def test_build_status_page_empty():
    page = build_status_page([])
    assert page.total_stacks == 0
    assert page.drift_rate == 0.0


def test_drift_rate(drifted_result, in_sync_result):
    page = build_status_page([drifted_result, in_sync_result])
    assert page.drift_rate == pytest.approx(0.5)


def test_render_html_contains_stack_names(drifted_result, in_sync_result):
    page = build_status_page([drifted_result, in_sync_result])
    html = render_status_html(page)
    assert "stack-a" in html
    assert "stack-b" in html


def test_render_html_shows_drifted_status(drifted_result):
    page = build_status_page([drifted_result])
    html = render_status_html(page)
    assert "DRIFTED" in html


def test_render_html_shows_in_sync_status(in_sync_result):
    page = build_status_page([in_sync_result])
    html = render_status_html(page)
    assert "IN_SYNC" in html


def test_render_text_contains_stack_names(drifted_result, in_sync_result):
    page = build_status_page([drifted_result, in_sync_result])
    text = render_status_text(page)
    assert "stack-a" in text
    assert "stack-b" in text


def test_render_text_shows_drift_rate(drifted_result, in_sync_result):
    page = build_status_page([drifted_result, in_sync_result])
    text = render_status_text(page)
    assert "50.0%" in text
