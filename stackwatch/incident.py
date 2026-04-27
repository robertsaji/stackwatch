"""Incident tracking for prolonged drift states."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from stackwatch.drift import DriftResult


class IncidentError(Exception):
    """Raised when incident operations fail."""


@dataclass
class Incident:
    incident_id: str
    stack_name: str
    opened_at: str
    closed_at: Optional[str] = None
    note: str = ""

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    def elapsed_hours(self) -> Optional[float]:
        start = datetime.fromisoformat(self.opened_at)
        end = datetime.fromisoformat(self.closed_at) if self.closed_at else datetime.now(timezone.utc)
        return (end - start).total_seconds() / 3600

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "stack_name": self.stack_name,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "note": self.note,
        }

    @staticmethod
    def from_dict(d: dict) -> "Incident":
        return Incident(
            incident_id=d["incident_id"],
            stack_name=d["stack_name"],
            opened_at=d["opened_at"],
            closed_at=d.get("closed_at"),
            note=d.get("note", ""),
        )


@dataclass
class IncidentStore:
    path: Path
    _incidents: List[Incident] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._incidents = []
            return
        try:
            data = json.loads(self.path.read_text())
            self._incidents = [Incident.from_dict(d) for d in data]
        except Exception as exc:
            raise IncidentError(f"Failed to load incidents: {exc}") from exc

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([i.to_dict() for i in self._incidents], indent=2))

    def open_incident(self, result: DriftResult, note: str = "") -> Incident:
        incident = Incident(
            incident_id=str(uuid.uuid4())[:8],
            stack_name=result.stack_name,
            opened_at=datetime.now(timezone.utc).isoformat(),
            note=note,
        )
        self._incidents.append(incident)
        self._save()
        return incident

    def close_incident(self, incident_id: str) -> Incident:
        for inc in self._incidents:
            if inc.incident_id == incident_id and inc.is_open:
                inc.closed_at = datetime.now(timezone.utc).isoformat()
                self._save()
                return inc
        raise IncidentError(f"No open incident found with id: {incident_id}")

    def open_for_stack(self, stack_name: str) -> List[Incident]:
        return [i for i in self._incidents if i.stack_name == stack_name and i.is_open]

    def all(self) -> List[Incident]:
        return list(self._incidents)
