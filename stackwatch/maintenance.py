"""Maintenance window support — suppress drift alerts during planned outages."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class MaintenanceError(Exception):
    """Raised for maintenance window configuration errors."""


@dataclass
class MaintenanceWindow:
    stack_name: str
    start: datetime
    end: datetime
    reason: str = ""

    def is_active(self, at: Optional[datetime] = None) -> bool:
        now = at or datetime.now(timezone.utc)
        return self.start <= now <= self.end

    def to_dict(self) -> dict:
        return {
            "stack_name": self.stack_name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MaintenanceWindow":
        return cls(
            stack_name=data["stack_name"],
            start=datetime.fromisoformat(data["start"]),
            end=datetime.fromisoformat(data["end"]),
            reason=data.get("reason", ""),
        )


@dataclass
class MaintenanceStore:
    path: Path
    _windows: List[MaintenanceWindow] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._windows = []
            return
        try:
            data = json.loads(self.path.read_text())
            self._windows = [MaintenanceWindow.from_dict(w) for w in data]
        except (json.JSONDecodeError, KeyError) as exc:
            raise MaintenanceError(f"Failed to load maintenance windows: {exc}") from exc

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([w.to_dict() for w in self._windows], indent=2))

    def add(self, window: MaintenanceWindow) -> None:
        if window.end <= window.start:
            raise MaintenanceError("end must be after start")
        self._windows.append(window)
        self._save()

    def remove(self, stack_name: str) -> int:
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.stack_name != stack_name]
        self._save()
        return before - len(self._windows)

    def active_windows(self, at: Optional[datetime] = None) -> List[MaintenanceWindow]:
        return [w for w in self._windows if w.is_active(at)]

    def is_suppressed(self, stack_name: str, at: Optional[datetime] = None) -> bool:
        return any(
            w.stack_name == stack_name and w.is_active(at)
            for w in self._windows
        )

    def all_windows(self) -> List[MaintenanceWindow]:
        return list(self._windows)
