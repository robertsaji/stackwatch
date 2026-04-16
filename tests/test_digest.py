"""Tests for stackwatch.digest."""
from __future__ import annotations

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.digest import build_digest, render_digest_text, render_digest_html


@pytest.fixture()
def results():
    return [
        DriftResult(
            stack_name="stack-a",
            status="DRIFTED",
            drifted_resources=[
                DriftedResource(logical_id="R1", resource_type="AWS::S3::Bucket", drift_status="MODIFIED")
            ],
        ),
        DriftResult(stack_name="stack-b", status="IN_SYNC", drifted_resources=[]),
    ]


def test_build_digest_total_stacks(results):
    digest = build_digest(results)
    assert digest.total_stacks == 2


def test_build_digest_drifted_stacks(results):
    digest = build_digest(results)
    assert digest.drifted_stacks == 1


def test_build_digest_empty():
    digest = build_digest([])
    assert digest.total_stacks == 0
    assert digest.drifted_stacks == 0


def test_render_text_contains_stack_names(results):
    digest = build_digest(results)
    text = render_digest_text(digest)
    assert "stack-a" in text
    assert "stack-b" in text


def test_render_text_shows_drift_indicator(results):
    digest = build_digest(results)
    text = render_digest_text(digest)
    assert "[DRIFT]" in text
    assert "[OK]" in text


def test_render_text_shows_counts(results):
    digest = build_digest(results)
    text = render_digest_text(digest)
    assert "Stacks checked : 2" in text
    assert "Drifted stacks : 1" in text


def test_render_html_contains_table(results):
    digest = build_digest(results)
    html = render_digest_html(digest)
    assert "<table>" in html
    assert "stack-a" in html


def test_render_html_shows_summary(results):
    digest = build_digest(results)
    html = render_digest_html(digest)
    assert "Checked: 2" in html
    assert "Drifted: 1" in html
