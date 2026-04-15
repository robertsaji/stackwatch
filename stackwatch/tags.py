"""Tag-based filtering and grouping for CloudFormation stacks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackwatch.drift import DriftResult


@dataclass
class TagFilter:
    """Filter drift results by stack tags."""

    required_tags: Dict[str, Optional[str]] = field(default_factory=dict)
    """Map of tag key -> expected value (None means key must exist, any value)."""

    def matches(self, tags: Dict[str, str]) -> bool:
        """Return True if *tags* satisfies all required_tags constraints."""
        for key, expected in self.required_tags.items():
            if key not in tags:
                return False
            if expected is not None and tags[key] != expected:
                return False
        return True

    def apply(self, results: List[DriftResult]) -> List[DriftResult]:
        """Return only results whose stack_tags match this filter."""
        return [r for r in results if self.matches(r.stack_tags)]


def group_by_tag(results: List[DriftResult], tag_key: str) -> Dict[str, List[DriftResult]]:
    """Group *results* by the value of *tag_key*.

    Stacks missing the tag are placed under the key ``"<untagged>"``.
    """
    groups: Dict[str, List[DriftResult]] = {}
    for result in results:
        value = result.stack_tags.get(tag_key, "<untagged>")
        groups.setdefault(value, []).append(result)
    return groups


def drift_rate_by_tag(results: List[DriftResult], tag_key: str) -> Dict[str, float]:
    """Return drift rate (0.0-1.0) per tag value for *tag_key*."""
    groups = group_by_tag(results, tag_key)
    rates: Dict[str, float] = {}
    for tag_value, group in groups.items():
        if not group:
            rates[tag_value] = 0.0
        else:
            drifted = sum(1 for r in group if r.has_drift)
            rates[tag_value] = drifted / len(group)
    return rates
