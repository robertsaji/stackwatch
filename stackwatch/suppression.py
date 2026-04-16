"""Drift suppression rules — silence alerts for known/expected drift."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from stackwatch.drift import DriftResult


class SuppressionError(Exception):
    """Raised when suppression store operations fail."""


@dataclass
class SuppressionRule:
    stack_name: str
    reason: str
    expires_at: Optional[str] = None  # ISO-8601 or None = permanent

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        expiry = datetime.fromisoformat(self.expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expiry

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SuppressionRule":
        return cls(**d)


@dataclass
class SuppressionStore:
    path: Path
    _rules: List[SuppressionRule] = field(default_factory=list, init=False)

    def load(self) -> None:
        if not self.path.exists():
            self._rules = []
            return
        try:
            data = json.loads(self.path.read_text())
            self._rules = [SuppressionRule.from_dict(r) for r in data]
        except Exception as exc:
            raise SuppressionError(f"Failed to load suppressions: {exc}") from exc

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps([r.to_dict() for r in self._rules], indent=2))
        except Exception as exc:
            raise SuppressionError(f"Failed to save suppressions: {exc}") from exc

    def add(self, rule: SuppressionRule) -> None:
        self._rules = [r for r in self._rules if r.stack_name != rule.stack_name]
        self._rules.append(rule)
        self.save()

    def remove(self, stack_name: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.stack_name != stack_name]
        if len(self._rules) < before:
            self.save()
            return True
        return False

    def is_suppressed(self, result: DriftResult) -> bool:
        for rule in self._rules:
            if rule.stack_name == result.stack_name:
                if rule.is_expired():
                    continue
                return True
        return False

    def active_rules(self) -> List[SuppressionRule]:
        return [r for r in self._rules if not r.is_expired()]
