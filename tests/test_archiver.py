"""Tests for stackwatch.archiver."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from stackwatch.archiver import ArchiveError, ArchiveEntry, DriftArchiver
from stackwatch.drift import DriftedResource, DriftResult
from stackwatch.snapshot import Snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(stack_name: str, drifted: bool = False) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="Res1", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})]
        if drifted
        else []
    )
    return DriftResult(stack_name=stack_name, drifted_resources=resources)


@pytest.fixture()
def archive_dir(tmp_path: Path) -> Path:
    return tmp_path / "archive"


@pytest.fixture()
def archiver(archive_dir: Path) -> DriftArchiver:
    return DriftArchiver(archive_dir=archive_dir)


def _make_snap(results=None) -> Snapshot:
    results = results or []
    return Snapshot(results=results)


# ---------------------------------------------------------------------------
# ArchiveEntry
# ---------------------------------------------------------------------------

def test_archive_entry_round_trip() -> None:
    entry = ArchiveEntry(timestamp="20240101T000000Z", filename="snap.json.gz", stack_count=3, drifted_count=1)
    assert ArchiveEntry.from_dict(entry.to_dict()) == entry


# ---------------------------------------------------------------------------
# DriftArchiver.archive
# ---------------------------------------------------------------------------

def test_archive_creates_gz_file(archiver: DriftArchiver, archive_dir: Path) -> None:
    snap = _make_snap([_make_result("stack-a")])
    entry = archiver.archive(snap)
    assert (archive_dir / entry.filename).exists()
    assert entry.filename.endswith(".json.gz")


def test_archive_index_is_updated(archiver: DriftArchiver, archive_dir: Path) -> None:
    snap = _make_snap([_make_result("stack-a"), _make_result("stack-b", drifted=True)])
    entry = archiver.archive(snap)
    assert entry.stack_count == 2
    assert entry.drifted_count == 1
    entries = archiver.list_entries()
    assert len(entries) == 1
    assert entries[0].filename == entry.filename


def test_archive_multiple_entries_accumulate(archiver: DriftArchiver) -> None:
    for i in range(3):
        archiver.archive(_make_snap([_make_result(f"stack-{i}")]))
    assert len(archiver.list_entries()) == 3


def test_gz_file_contains_valid_json(archiver: DriftArchiver, archive_dir: Path) -> None:
    snap = _make_snap([_make_result("stack-x")])
    entry = archiver.archive(snap)
    with gzip.open(archive_dir / entry.filename, "rb") as fh:
        data = json.loads(fh.read())
    assert "results" in data


# ---------------------------------------------------------------------------
# DriftArchiver.load
# ---------------------------------------------------------------------------

def test_load_returns_snapshot(archiver: DriftArchiver) -> None:
    original = _make_snap([_make_result("stack-y", drifted=True)])
    entry = archiver.archive(original)
    loaded = archiver.load(entry.filename)
    assert len(loaded.stack_names()) == 1
    assert "stack-y" in loaded.stack_names()


def test_load_raises_for_missing_file(archiver: DriftArchiver) -> None:
    with pytest.raises(ArchiveError, match="not found"):
        archiver.load("nonexistent.json.gz")


# ---------------------------------------------------------------------------
# list_entries on empty / corrupt index
# ---------------------------------------------------------------------------

def test_list_returns_empty_when_no_archive(archiver: DriftArchiver) -> None:
    assert archiver.list_entries() == []


def test_load_index_raises_on_corrupt_json(archiver: DriftArchiver, archive_dir: Path) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.json").write_text("NOT JSON")
    with pytest.raises(ArchiveError, match="Corrupt"):
        archiver.list_entries()
