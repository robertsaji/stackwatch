"""Drift alert deduplication — suppresses repeated alerts for already-known drift."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from stackwatch.drift import DriftResult


class DedupError(Exception):
    """Raised when the dedup store cannot be read or written."""


def _fingerprint(result: DriftResult) -> str:
    """Return a stable hash that identifies a specific drift state for a stack."""
    resource_ids = sorted(
        r.resource_id for r in result.drifted_resources
    )
    payload = json.dumps({"stack": result.stack_name, "resources": resource_ids}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class DedupEntry:
    stack_name: str
    fingerprint: str
    first_seen: float
    last_seen: float

    def to_dict(self) -> dict:
        return {
            "stack_name": self.stack_name,
            "fingerprint": self.fingerprint,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @staticmethod
    def from_dict(d: dict) -> "DedupEntry":
        return DedupEntry(
            stack_name=d["stack_name"],
            fingerprint=d["fingerprint"],
            first_seen=d["first_seen"],
            last_seen=d["last_seen"],
        )


@dataclass
class DedupStore:
    path: Path
    _entries: Dict[str, DedupEntry] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
            self._entries = {
                k: DedupEntry.from_dict(v) for k, v in raw.items()
            }
        except Exception as exc:  # pragma: no cover
            raise DedupError(f"Failed to load dedup store: {exc}") from exc

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({k: v.to_dict() for k, v in self._entries.items()}, indent=2)
            )
        except Exception as exc:  # pragma: no cover
            raise DedupError(f"Failed to save dedup store: {exc}") from exc

    def is_duplicate(self, result: DriftResult) -> bool:
        """Return True if this exact drift state has already been seen."""
        if not result.has_drift:
            return False
        fp = _fingerprint(result)
        entry = self._entries.get(result.stack_name)
        return entry is not None and entry.fingerprint == fp

    def record(self, result: DriftResult) -> None:
        """Record the current drift state; call after deciding to send an alert."""
        if not result.has_drift:
            self._entries.pop(result.stack_name, None)
        else:
            fp = _fingerprint(result)
            now = time.time()
            existing = self._entries.get(result.stack_name)
            first_seen = existing.first_seen if existing else now
            self._entries[result.stack_name] = DedupEntry(
                stack_name=result.stack_name,
                fingerprint=fp,
                first_seen=first_seen,
                last_seen=now,
            )
        self._save()

    def clear(self, stack_name: Optional[str] = None) -> None:
        """Remove one stack or all entries from the store."""
        if stack_name:
            self._entries.pop(stack_name, None)
        else:
            self._entries.clear()
        self._save()

    def all_entries(self) -> List[DedupEntry]:
        return list(self._entries.values())
