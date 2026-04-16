"""Tests for stackwatch.audit."""
import pytest
from pathlib import Path

from stackwatch.audit import AuditLog, AuditEntry, AuditError
from stackwatch.drift import DriftResult, DriftedResource


@pytest.fixture
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "audit" / "log.json"


@pytest.fixture
def audit(audit_path: Path) -> AuditLog:
    return AuditLog(audit_path)


def _make_result(name: str, drifted: bool = False) -> DriftResult:
    resources = [
        DriftedResource(logical_id="Res1", resource_type="AWS::S3::Bucket", drift_status="MODIFIED", expected={}, actual={})
    ] if drifted else []
    return DriftResult(
        stack_name=name,
        status="DRIFTED" if drifted else "IN_SYNC",
        drifted_resources=resources,
    )


def test_load_returns_empty_when_no_file(audit: AuditLog):
    assert audit.entries() == []


def test_record_creates_file(audit: AuditLog, audit_path: Path):
    result = _make_result("stack-a")
    audit.record(result)
    assert audit_path.exists()


def test_record_entry_fields(audit: AuditLog):
    result = _make_result("stack-b", drifted=True)
    entry = audit.record(result, note="manual check")
    assert entry.stack_name == "stack-b"
    assert entry.status == "DRIFTED"
    assert entry.drifted_count == 1
    assert entry.note == "manual check"


def test_entries_filtered_by_stack(audit: AuditLog):
    audit.record(_make_result("stack-a"))
    audit.record(_make_result("stack-b", drifted=True))
    audit.record(_make_result("stack-a", drifted=True))
    assert len(audit.entries("stack-a")) == 2
    assert len(audit.entries("stack-b")) == 1


def test_entries_all(audit: AuditLog):
    audit.record(_make_result("stack-a"))
    audit.record(_make_result("stack-b"))
    assert len(audit.entries()) == 2


def test_persists_across_instances(audit_path: Path):
    log1 = AuditLog(audit_path)
    log1.record(_make_result("stack-x", drifted=True))
    log2 = AuditLog(audit_path)
    assert len(log2.entries()) == 1
    assert log2.entries()[0].stack_name == "stack-x"


def test_clear_removes_entries(audit: AuditLog):
    audit.record(_make_result("stack-a"))
    audit.clear()
    assert audit.entries() == []


def test_load_raises_on_corrupt_file(audit_path: Path):
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("not json{{{")
    with pytest.raises(AuditError):
        AuditLog(audit_path)
