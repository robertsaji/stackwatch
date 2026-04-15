"""Stack filtering utilities for stackwatch."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.drift import DriftResult


@dataclass
class FilterConfig:
    """Configuration for stack filtering."""

    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    statuses: List[str] = field(default_factory=list)


class StackFilter:
    """Filters DriftResult objects based on name patterns and drift status."""

    def __init__(self, config: Optional[FilterConfig] = None) -> None:
        self._config = config or FilterConfig()

    def _matches_include(self, name: str) -> bool:
        patterns = self._config.include_patterns
        if not patterns:
            return True
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    def _matches_exclude(self, name: str) -> bool:
        patterns = self._config.exclude_patterns
        if not patterns:
            return False
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    def _matches_status(self, result: DriftResult) -> bool:
        statuses = self._config.statuses
        if not statuses:
            return True
        return result.drift_status in statuses

    def apply(self, results: List[DriftResult]) -> List[DriftResult]:
        """Return only the results that pass all filter criteria."""
        filtered: List[DriftResult] = []
        for result in results:
            name = result.stack_name
            if not self._matches_include(name):
                continue
            if self._matches_exclude(name):
                continue
            if not self._matches_status(result):
                continue
            filtered.append(result)
        return filtered
