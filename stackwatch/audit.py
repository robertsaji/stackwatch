"""Audit log for drift detection events."""
from __future__ import annotations

import json
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from stackwatch.drift import DriftResult


class AuditError(Exception):
    pass


@dataclass
class AuditEntry:
    timestamp: str
    stack_name: str
    status: str
    drifted_count: int
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "stack_name": self.stack_name,
            "status": self.status,
            "drifted_count": self.drifted_count,
            "note": self.note,
        }

    @staticmethod
    def from_dict(d: dict) -> "AuditEntry":
        return AuditEntry(
            timestamp=d["timestamp"],
            stack_name=d["stack_name"],
            status=d["status"],
            drifted_count=d["drifted_count"],
            note=d.get("note", ""),
        )

    @staticmethod
    def from_result(result: DriftResult, note: str = "") -> "AuditEntry":
        return AuditEntry(
            timestamp=datetime.datetime.utcnow().isoformat(),
            stack_name=result.stack_name,
            status=result.status,
            drifted_count=len(result.drifted_resources),
            note=note,
        )


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._entries: List[AuditEntry] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            self._entries = [AuditEntry.from_dict(e) for e in data]
        except Exception as exc:
            raise AuditError(f"Failed to load audit log: {exc}") from exc

    def record(self, result: DriftResult, note: str = "") -> AuditEntry:
        entry = AuditEntry.from_result(result, note=note)
        self._entries.append(entry)
        self._save()
        return entry

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))
        except Exception as exc:
            raise AuditError(f"Failed to save audit log: {exc}") from exc

    def entries(self, stack_name: Optional[str] = None) -> List[AuditEntry]:
        if stack_name is None:
            return list(self._entries)
        return [e for e in self._entries if e.stack_name == stack_name]

    def clear(self) -> None:
        self._entries = []
        self._save()
