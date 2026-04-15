"""High-level manager that combines drift detection, alerting, and notification."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from stackwatch.alerting import AlertStore
from stackwatch.drift import DriftDetector, DriftResult
from stackwatch.notifier import Notifier


@dataclass
class AlertManagerConfig:
    cooldown_seconds: float = 3600.0
    store_path: Path = Path(".stackwatch/alert_store.json")
    dry_run: bool = False


@dataclass
class AlertManager:
    """Orchestrates drift detection, suppression, and notification."""

    detector: DriftDetector
    notifiers: List[Notifier]
    config: AlertManagerConfig = field(default_factory=AlertManagerConfig)
    _store: Optional[AlertStore] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._store = AlertStore(
            path=self.config.store_path,
            cooldown_seconds=self.config.cooldown_seconds,
        )

    def run(self, stack_names: List[str]) -> List[DriftResult]:
        """Detect drift for *stack_names* and send alerts where appropriate.

        Returns the list of DriftResult objects regardless of whether alerts
        were suppressed.
        """
        results = self.detector.detect_all(stack_names)
        for result in results:
            if self._store.should_alert(result):
                if not self.config.dry_run:
                    for notifier in self.notifiers:
                        notifier.send(result)
                    self._store.record_alert(result)
        return results

    def reset(self, stack_name: Optional[str] = None) -> None:
        """Clear suppression records for *stack_name* or all stacks."""
        self._store.clear(stack_name)
