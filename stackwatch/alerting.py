"""Alert suppression and deduplication for drift notifications."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from stackwatch.drift import DriftResult


class AlertError(Exception):
    """Raised when the alert store cannot be read or written."""


@dataclass
class AlertRecord:
    stack_name: str
    fingerprint: str
    first_seen: float
    last_sent: float
    send_count: int = 1

    def to_dict(self) -> dict:
        return {
            "stack_name": self.stack_name,
            "fingerprint": self.fingerprint,
            "first_seen": self.first_seen,
            "last_sent": self.last_sent,
            "send_count": self.send_count,
        }

    @staticmethod
    def from_dict(data: dict) -> "AlertRecord":
        return AlertRecord(
            stack_name=data["stack_name"],
            fingerprint=data["fingerprint"],
            first_seen=data["first_seen"],
            last_sent=data["last_sent"],
            send_count=data["send_count"],
        )


def _fingerprint(result: DriftResult) -> str:
    """Return a stable hash representing the current drift state."""
    resource_ids = sorted(r.logical_id for r in result.drifted_resources)
    payload = json.dumps({"stack": result.stack_name, "resources": resource_ids}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class AlertStore:
    """Persist alert records to avoid duplicate notifications."""

    path: Path
    cooldown_seconds: float = 3600.0
    _records: Dict[str, AlertRecord] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            self._records = {k: AlertRecord.from_dict(v) for k, v in data.items()}
        except Exception as exc:
            raise AlertError(f"Failed to load alert store: {exc}") from exc

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({k: v.to_dict() for k, v in self._records.items()}, indent=2))
        except Exception as exc:
            raise AlertError(f"Failed to save alert store: {exc}") from exc

    def should_alert(self, result: DriftResult) -> bool:
        """Return True if an alert should be sent for *result*."""
        if not result.has_drift:
            return False
        fp = _fingerprint(result)
        record = self._records.get(result.stack_name)
        now = time.time()
        if record is None or record.fingerprint != fp:
            return True
        return (now - record.last_sent) >= self.cooldown_seconds

    def record_alert(self, result: DriftResult) -> None:
        """Mark an alert as sent for *result*."""
        fp = _fingerprint(result)
        now = time.time()
        existing = self._records.get(result.stack_name)
        if existing and existing.fingerprint == fp:
            existing.last_sent = now
            existing.send_count += 1
        else:
            self._records[result.stack_name] = AlertRecord(
                stack_name=result.stack_name,
                fingerprint=fp,
                first_seen=now,
                last_sent=now,
            )
        self._save()

    def clear(self, stack_name: Optional[str] = None) -> None:
        """Remove records for *stack_name* or all records if None."""
        if stack_name is None:
            self._records.clear()
        else:
            self._records.pop(stack_name, None)
        self._save()
