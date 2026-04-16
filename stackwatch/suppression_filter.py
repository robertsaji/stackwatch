"""Apply suppression rules when filtering drift results before alerting."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from stackwatch.drift import DriftResult
from stackwatch.suppression import SuppressionStore


@dataclass
class SuppressionFilterResult:
    allowed: List[DriftResult]
    suppressed: List[DriftResult]

    @property
    def summary(self) -> str:
        """Return a human-readable summary of the filter result."""
        return (
            f"{len(self.allowed)} allowed, {len(self.suppressed)} suppressed "
            f"(total {len(self.allowed) + len(self.suppressed)})"
        )


class SuppressionFilter:
    """Wraps a SuppressionStore and partitions drift results."""

    def __init__(self, store: SuppressionStore) -> None:
        self._store = store

    @classmethod
    def from_path(cls, path: Path) -> "SuppressionFilter":
        store = SuppressionStore(path=path)
        store.load()
        return cls(store)

    def apply(self, results: List[DriftResult]) -> SuppressionFilterResult:
        allowed: List[DriftResult] = []
        suppressed: List[DriftResult] = []
        for result in results:
            if self._store.is_suppressed(result):
                suppressed.append(result)
            else:
                allowed.append(result)
        return SuppressionFilterResult(allowed=allowed, suppressed=suppressed)

    def is_suppressed(self, result: DriftResult) -> bool:
        return self._store.is_suppressed(result)
