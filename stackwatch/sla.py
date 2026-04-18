"""SLA tracking for drift resolution."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path


class SLAError(Exception):
    pass


@dataclass
class SLAConfig:
    max_drift_hours: float = 24.0
    warning_threshold: float = 0.75  # fraction of max before warning

    def __post_init__(self) -> None:
        if self.max_drift_hours <= 0:
            raise SLAError("max_drift_hours must be positive")
        if not (0 < self.warning_threshold < 1):
            raise SLAError("warning_threshold must be between 0 and 1")


@dataclass
class SLAStatus:
    stack_name: str
    first_drifted_at: datetime
    deadline: datetime
    now: datetime = field(default_factory=datetime.utcnow)

    @property
    def elapsed_hours(self) -> float:
        return (self.now - self.first_drifted_at).total_seconds() / 3600

    @property
    def remaining_hours(self) -> float:
        return (self.deadline - self.now).total_seconds() / 3600

    @property
    def breached(self) -> bool:
        return self.now >= self.deadline

    def warning(self, config: SLAConfig) -> bool:
        total = config.max_drift_hours
        return not self.breached and self.elapsed_hours >= total * config.warning_threshold


@dataclass
class SLATracker:
    path: Path
    config: SLAConfig = field(default_factory=SLAConfig)
    _records: Dict[str, str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._records = json.loads(self.path.read_text())

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._records, indent=2))

    def record_drift(self, stack_name: str, at: Optional[datetime] = None) -> None:
        if stack_name not in self._records:
            ts = (at or datetime.utcnow()).isoformat()
            self._records[stack_name] = ts
            self._save()

    def clear(self, stack_name: str) -> None:
        if stack_name in self._records:
            del self._records[stack_name]
            self._save()

    def status(self, stack_name: str, now: Optional[datetime] = None) -> Optional[SLAStatus]:
        if stack_name not in self._records:
            return None
        first = datetime.fromisoformat(self._records[stack_name])
        deadline = first + timedelta(hours=self.config.max_drift_hours)
        return SLAStatus(stack_name=stack_name, first_drifted_at=first, deadline=deadline, now=now or datetime.utcnow())

    def all_statuses(self, now: Optional[datetime] = None) -> List[SLAStatus]:
        return [self.status(n, now) for n in self._records]
