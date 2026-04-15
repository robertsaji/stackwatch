"""Drift history tracking: persist and query past drift run results."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from stackwatch.drift import DriftResult


class HistoryError(Exception):
    """Raised when history storage operations fail."""


@dataclass
class HistoryEntry:
    timestamp: str  # ISO-8601
    stack_name: str
    region: str
    drifted: bool
    drifted_resource_count: int

    @staticmethod
    def from_result(result: DriftResult) -> "HistoryEntry":
        return HistoryEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stack_name=result.stack_name,
            region=result.region,
            drifted=result.drifted,
            drifted_resource_count=len(result.drifted_resources),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "HistoryEntry":
        return HistoryEntry(**data)


class DriftHistory:
    """Append-only JSON-lines store for drift run history."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def record(self, result: DriftResult) -> HistoryEntry:
        """Append a new entry derived from *result* and return it."""
        entry = HistoryEntry.from_result(result)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict()) + "\n")
        except OSError as exc:
            raise HistoryError(f"Failed to write history: {exc}") from exc
        return entry

    def load(self, stack_name: Optional[str] = None) -> List[HistoryEntry]:
        """Return all entries, optionally filtered by *stack_name*."""
        if not self._path.exists():
            return []
        entries: List[HistoryEntry] = []
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    entry = HistoryEntry.from_dict(json.loads(line))
                    if stack_name is None or entry.stack_name == stack_name:
                        entries.append(entry)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise HistoryError(f"Failed to read history: {exc}") from exc
        return entries

    def clear(self) -> None:
        """Delete the history file if it exists."""
        try:
            if self._path.exists():
                self._path.unlink()
        except OSError as exc:
            raise HistoryError(f"Failed to clear history: {exc}") from exc
