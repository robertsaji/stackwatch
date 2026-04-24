"""Group drift results by environment tag or name prefix for summary reporting."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackwatch.drift import DriftResult


@dataclass
class GroupingConfig:
    """Configuration for stack grouping strategy."""

    tag_key: Optional[str] = None  # e.g. "Environment"
    prefix_delimiter: Optional[str] = None  # e.g. "-" splits "prod-api" -> "prod"
    fallback_group: str = "ungrouped"

    def __post_init__(self) -> None:
        if self.tag_key and self.prefix_delimiter:
            raise ValueError("Specify only one of tag_key or prefix_delimiter, not both.")


@dataclass
class StackGroup:
    """A named group containing one or more drift results."""

    name: str
    results: List[DriftResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def drifted(self) -> int:
        return sum(1 for r in self.results if r.has_drift)

    @property
    def drift_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.drifted / self.total


@dataclass
class GroupingReport:
    """Aggregated grouping report."""

    groups: List[StackGroup] = field(default_factory=list)

    @property
    def total_stacks(self) -> int:
        return sum(g.total for g in self.groups)

    @property
    def drifted_stacks(self) -> int:
        return sum(g.drifted for g in self.groups)


def _group_key(result: DriftResult, config: GroupingConfig) -> str:
    if config.tag_key:
        tags = result.tags if hasattr(result, "tags") and result.tags else {}
        return tags.get(config.tag_key, config.fallback_group)
    if config.prefix_delimiter:
        parts = result.stack_name.split(config.prefix_delimiter, 1)
        return parts[0] if len(parts) > 1 else config.fallback_group
    return config.fallback_group


def build_grouping_report(
    results: List[DriftResult], config: GroupingConfig
) -> GroupingReport:
    """Partition results into named groups according to config."""
    buckets: Dict[str, StackGroup] = {}
    for result in results:
        key = _group_key(result, config)
        if key not in buckets:
            buckets[key] = StackGroup(name=key)
        buckets[key].results.append(result)
    return GroupingReport(groups=list(buckets.values()))


def render_grouping_text(report: GroupingReport) -> str:
    """Render a grouping report as plain text."""
    lines = ["Stack Groups", "============"]
    for group in sorted(report.groups, key=lambda g: g.name):
        pct = f"{group.drift_rate * 100:.0f}%"
        lines.append(
            f"  {group.name}: {group.drifted}/{group.total} drifted ({pct})"
        )
    lines.append(f"Total: {report.drifted_stacks}/{report.total_stacks} drifted")
    return "\n".join(lines)
