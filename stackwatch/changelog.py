"""Track and render a changelog of drift state transitions per stack."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from stackwatch.drift import DriftResult


class ChangelogError(Exception):
    """Raised when changelog operations fail."""


@dataclass
class ChangelogEntry:
    stack_name: str
    previous_state: str  # "IN_SYNC" | "DRIFTED" | "UNKNOWN"
    current_state: str
    drifted_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "stack_name": self.stack_name,
            "previous_state": self.previous_state,
            "current_state": self.current_state,
            "drifted_count": self.drifted_count,
            "timestamp": self.timestamp.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "ChangelogEntry":
        return ChangelogEntry(
            stack_name=data["stack_name"],
            previous_state=data["previous_state"],
            current_state=data["current_state"],
            drifted_count=data["drifted_count"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class Changelog:
    path: Path
    _entries: List[ChangelogEntry] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._entries = self._load()

    def _load(self) -> List[ChangelogEntry]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text())
            return [ChangelogEntry.from_dict(e) for e in data]
        except (json.JSONDecodeError, KeyError) as exc:
            raise ChangelogError(f"Failed to load changelog: {exc}") from exc

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))

    def record(self, result: DriftResult, previous_state: Optional[str] = None) -> Optional[ChangelogEntry]:
        """Record a transition if the state changed. Returns entry if recorded."""
        current = "DRIFTED" if result.has_drift else "IN_SYNC"
        prev = previous_state or "UNKNOWN"
        if prev == current:
            return None
        entry = ChangelogEntry(
            stack_name=result.stack_name,
            previous_state=prev,
            current_state=current,
            drifted_count=len(result.drifted_resources),
        )
        self._entries.append(entry)
        self._save()
        return entry

    def entries_for(self, stack_name: str) -> List[ChangelogEntry]:
        return [e for e in self._entries if e.stack_name == stack_name]

    def all_entries(self) -> List[ChangelogEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries = []
        self._save()


def render_changelog_text(changelog: Changelog) -> str:
    entries = changelog.all_entries()
    if not entries:
        return "No changelog entries."
    lines = ["Drift Changelog", "=" * 40]
    for e in entries:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"[{ts}] {e.stack_name}: {e.previous_state} -> {e.current_state} ({e.drifted_count} drifted)")
    return "\n".join(lines)
