"""Tests for stackwatch.cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stackwatch.cache import CacheError, DriftCache
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture()
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "test_cache.json"


@pytest.fixture()
def cache(cache_path: Path) -> DriftCache:
    return DriftCache(path=cache_path)


def _make_result(stack_name: str = "my-stack", status: str = "DRIFTED") -> DriftResult:
    return DriftResult(
        stack_name=stack_name,
        status=status,
        drifted_resources=[
            DriftedResource(
                logical_id="MyBucket",
                resource_type="AWS::S3::Bucket",
                drift_status="MODIFIED",
            )
        ],
    )


def test_get_returns_none_when_cache_missing(cache: DriftCache) -> None:
    assert cache.get("nonexistent-stack") is None


def test_set_and_get_round_trip(cache: DriftCache) -> None:
    result = _make_result()
    cache.set(result)
    retrieved = cache.get(result.stack_name)
    assert retrieved is not None
    assert retrieved.stack_name == result.stack_name
    assert retrieved.status == result.status
    assert len(retrieved.drifted_resources) == 1
    assert retrieved.drifted_resources[0].logical_id == "MyBucket"


def test_set_overwrites_previous_entry(cache: DriftCache) -> None:
    cache.set(_make_result(status="DRIFTED"))
    cache.set(_make_result(status="IN_SYNC"))
    retrieved = cache.get("my-stack")
    assert retrieved is not None
    assert retrieved.status == "IN_SYNC"


def test_has_changed_true_when_no_cache(cache: DriftCache) -> None:
    assert cache.has_changed(_make_result()) is True


def test_has_changed_false_when_same(cache: DriftCache) -> None:
    result = _make_result()
    cache.set(result)
    assert cache.has_changed(result) is False


def test_has_changed_true_when_status_differs(cache: DriftCache) -> None:
    cache.set(_make_result(status="IN_SYNC"))
    assert cache.has_changed(_make_result(status="DRIFTED")) is True


def test_multiple_stacks_stored_independently(cache: DriftCache) -> None:
    r1 = _make_result(stack_name="stack-a", status="IN_SYNC")
    r2 = _make_result(stack_name="stack-b", status="DRIFTED")
    cache.set(r1)
    cache.set(r2)
    assert cache.get("stack-a").status == "IN_SYNC"
    assert cache.get("stack-b").status == "DRIFTED"


def test_load_raises_cache_error_on_corrupt_file(cache_path: Path) -> None:
    cache_path.write_text("not-valid-json")
    cache = DriftCache(path=cache_path)
    with pytest.raises(CacheError):
        cache.get("any-stack")
