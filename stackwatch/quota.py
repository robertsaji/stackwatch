"""AWS service quota awareness for drift detection rate limiting."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import time


class QuotaError(Exception):
    pass


@dataclass
class QuotaConfig:
    max_detections_per_minute: int = 10
    max_concurrent_stacks: int = 20

    def __post_init__(self) -> None:
        if self.max_detections_per_minute < 1:
            raise QuotaError("max_detections_per_minute must be >= 1")
        if self.max_concurrent_stacks < 1:
            raise QuotaError("max_concurrent_stacks must be >= 1")


@dataclass
class QuotaUsage:
    stack_name: str
    detected_at: float = field(default_factory=time.time)


@dataclass
class QuotaTracker:
    config: QuotaConfig
    _history: List[QuotaUsage] = field(default_factory=list, init=False)

    def _prune(self) -> None:
        cutoff = time.time() - 60.0
        self._history = [u for u in self._history if u.detected_at >= cutoff]

    def can_detect(self) -> bool:
        self._prune()
        return len(self._history) < self.config.max_detections_per_minute

    def record(self, stack_name: str) -> None:
        if not self.can_detect():
            raise QuotaError(
                f"Detection quota exceeded: max {self.config.max_detections_per_minute} per minute"
            )
        self._history.append(QuotaUsage(stack_name=stack_name))

    def usage_count(self) -> int:
        self._prune()
        return len(self._history)

    def remaining(self) -> int:
        return max(0, self.config.max_detections_per_minute - self.usage_count())

    def stacks_detected(self) -> List[str]:
        self._prune()
        return [u.stack_name for u in self._history]
