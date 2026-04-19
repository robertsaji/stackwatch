"""Tests for stackwatch.runbook_enricher."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.runbook import RunbookStore
from stackwatch.runbook_enricher import EnrichedResult, enrich, render_enriched_text


def _make_result(name: str, drifted: bool = False) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="R", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=["BucketName"])]
        if drifted
        else []
    )
    return DriftResult(stack_name=name, status="DRIFTED" if drifted else "IN_SYNC", drifted_resources=resources)


@pytest.fixture
def store(tmp_path: Path) -> RunbookStore:
    s = RunbookStore(path=tmp_path / "rb.json")
    s.set("stack-a", "https://wiki.example.com/stack-a")
    return s


def test_enrich_attaches_url(store: RunbookStore) -> None:
    results = [_make_result("stack-a", drifted=True)]
    enriched = enrich(results, store)
    assert len(enriched) == 1
    assert enriched[0].runbook_url == "https://wiki.example.com/stack-a"
    assert enriched[0].has_runbook is True


def test_enrich_missing_url_is_none(store: RunbookStore) -> None:
    results = [_make_result("unknown-stack")]
    enriched = enrich(results, store)
    assert enriched[0].runbook_url is None
    assert enriched[0].has_runbook is False


def test_enrich_preserves_order(store: RunbookStore) -> None:
    results = [_make_result("z"), _make_result("a"), _make_result("stack-a")]
    enriched = enrich(results, store)
    assert [e.stack_name for e in enriched] == ["z", "a", "stack-a"]


def test_render_enriched_text_drifted_with_runbook(store: RunbookStore) -> None:
    results = [_make_result("stack-a", drifted=True)]
    text = render_enriched_text(enrich(results, store))
    assert "DRIFTED" in text
    assert "stack-a" in text
    assert "https://wiki.example.com/stack-a" in text


def test_render_enriched_text_in_sync_no_runbook(store: RunbookStore) -> None:
    results = [_make_result("other")]
    text = render_enriched_text(enrich(results, store))
    assert "IN_SYNC" in text
    assert "runbook" not in text
