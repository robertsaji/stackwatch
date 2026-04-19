"""Watchdog: detects when drift detection itself fails repeatedly and raises alerts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


class WatchdogError(Exception):
    pass


@dataclass
class WatchdogConfig:
    max_consecutive_failures: int = 3
    notify_on_recovery: bool = True

    def __post_init__(self) -> None:
        if self.max_consecutive_failures < 1:
            raise WatchdogError("max_consecutive_failures must be >= 1")


@dataclass
class WatchdogState:
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    alerted: bool = False
    failure_messages: List[str] = field(default_factory=list)

    def record_failure(self, message: str) -> None:
        self.consecutive_failures += 1
        self.last_failure_at = datetime.now(timezone.utc)
        self.failure_messages.append(message)

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.alerted = False
        self.last_success_at = datetime.now(timezone.utc)
        self.failure_messages.clear()

    @property
    def is_healthy(self) -> bool:
        return self.consecutive_failures == 0


class Watchdog:
    def __init__(self, config: WatchdogConfig, notifier) -> None:
        self._config = config
        self._notifier = notifier
        self._state = WatchdogState()

    @property
    def state(self) -> WatchdogState:
        return self._state

    def on_success(self) -> None:
        was_alerted = self._state.alerted
        self._state.record_success()
        if was_alerted and self._config.notify_on_recovery:
            self._notifier.send_text("[StackWatch Watchdog] Drift detection recovered successfully.")

    def on_failure(self, message: str) -> None:
        self._state.record_failure(message)
        if (
            self._state.consecutive_failures >= self._config.max_consecutive_failures
            and not self._state.alerted
        ):
            self._state.alerted = True
            summary = "\n".join(self._state.failure_messages[-self._config.max_consecutive_failures:])
            self._notifier.send_text(
                f"[StackWatch Watchdog] Drift detection has failed "
                f"{self._state.consecutive_failures} consecutive time(s):\n{summary}"
            )
