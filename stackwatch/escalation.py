"""Escalation policy: notify different channels based on drift severity."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from stackwatch.severity import SeverityLevel, classify
from stackwatch.drift import DriftResult
from stackwatch.notifier import Notifier


class EscalationError(Exception):
    pass


@dataclass
class EscalationRule:
    min_level: SeverityLevel
    notifier_name: str

    def matches(self, level: SeverityLevel) -> bool:
        return level.value >= self.min_level.value


@dataclass
class EscalationConfig:
    rules: List[EscalationRule] = field(default_factory=list)

    def rules_for(self, level: SeverityLevel) -> List[EscalationRule]:
        return [r for r in self.rules if r.matches(level)]


@dataclass
class EscalationManager:
    config: EscalationConfig
    notifiers: dict  # name -> Notifier

    def handle(self, result: DriftResult) -> List[str]:
        """Send alerts via matching notifiers; return list of notifier names used."""
        severity = classify(result)
        matching_rules = self.config.rules_for(severity.level)
        used: List[str] = []
        for rule in matching_rules:
            notifier: Optional[Notifier] = self.notifiers.get(rule.notifier_name)
            if notifier is None:
                raise EscalationError(f"Unknown notifier: {rule.notifier_name}")
            notifier.send(result)
            used.append(rule.notifier_name)
        return used

    def handle_all(self, results: List[DriftResult]) -> dict:
        """Handle a list of results; return mapping stack_name -> notifiers used."""
        return {r.stack_name: self.handle(r) for r in results}
