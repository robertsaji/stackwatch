"""Tests for stackwatch.summary."""
import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.summary import (
    RunSummary,
    StackSummary,
    build_summary,
    render_summary_text,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
        status="DRIFTED",
        drifted_resources=[drifted_resource],
    )


@pytest.fixture()
def in_sync_result():
    return DriftResult(
        stack_name="staging-stack",
        status="IN_SYNC",
        drifted_resources=[],
    )


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------

def test_build_summary_empty():
    summary = build_summary([])
    assert summary.total_stacks == 0
    assert summary.drifted_stacks == 0
    assert summary.drift_rate == 0.0


def test_build_summary_counts(drifted_result, in_sync_result):
    summary = build_summary([drifted_result, in_sync_result])
    assert summary.total_stacks == 2
    assert summary.drifted_stacks == 1
    assert summary.in_sync_stacks == 1
    assert summary.total_drifted_resources == 1


def test_build_summary_drift_rate(drifted_result, in_sync_result):
    summary = build_summary([drifted_result, in_sync_result])
    assert summary.drift_rate == pytest.approx(0.5)


def test_build_summary_stack_entries(drifted_result, in_sync_result):
    summary = build_summary([drifted_result, in_sync_result])
    names = [s.stack_name for s in summary.stacks]
    assert "prod-stack" in names
    assert "staging-stack" in names


def test_build_summary_resource_types(drifted_result):
    summary = build_summary([drifted_result])
    prod = next(s for s in summary.stacks if s.stack_name == "prod-stack")
    assert "AWS::S3::Bucket" in prod.resource_types


# ---------------------------------------------------------------------------
# render_summary_text
# ---------------------------------------------------------------------------

def test_render_summary_text_contains_counts(drifted_result, in_sync_result):
    summary = build_summary([drifted_result, in_sync_result])
    text = render_summary_text(summary)
    assert "Stacks checked : 2" in text
    assert "Drifted        : 1" in text
    assert "In sync        : 1" in text


def test_render_summary_text_drift_marker(drifted_result):
    summary = build_summary([drifted_result])
    text = render_summary_text(summary)
    assert "[DRIFT]" in text
    assert "prod-stack" in text


def test_render_summary_text_ok_marker(in_sync_result):
    summary = build_summary([in_sync_result])
    text = render_summary_text(summary)
    assert "[OK]" in text
    assert "staging-stack" in text
