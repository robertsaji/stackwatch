"""Correlate drift events across stacks to find common patterns."""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from typing import List, Dict
from stackwatch.drift import DriftResult


@dataclass
class CorrelationGroup:
    resource_type: str
    stacks: List[str]
    count: int

    def __str__(self) -> str:
        return f"{self.resource_type}: {self.count} stacks ({', '.join(self.stacks)})"


@dataclass
class CorrelationReport:
    groups: List[CorrelationGroup] = field(default_factory=list)

    @property
    def has_correlations(self) -> bool:
        return any(g.count > 1 for g in self.groups)

    def top(self, n: int = 5) -> List[CorrelationGroup]:
        return sorted(self.groups, key=lambda g: g.count, reverse=True)[:n]


def build_correlation_report(results: List[DriftResult]) -> CorrelationReport:
    """Group drifted resource types across stacks."""
    type_to_stacks: Dict[str, List[str]] = defaultdict(list)

    for result in results:
        if not result.has_drift:
            continue
        seen_types: set = set()
        for resource in result.drifted_resources:
            rt = resource.resource_type
            if rt not in seen_types:
                type_to_stacks[rt].append(result.stack_name)
                seen_types.add(rt)

    groups = [
        CorrelationGroup(resource_type=rt, stacks=stacks, count=len(stacks))
        for rt, stacks in type_to_stacks.items()
    ]
    return CorrelationReport(groups=groups)


def render_correlation_text(report: CorrelationReport) -> str:
    lines = ["=== Drift Correlation Report ==="]
    if not report.groups:
        lines.append("No correlated drift found.")
        return "\n".join(lines)
    for group in report.top():
        lines.append(f"  {group}")
    return "\n".join(lines)
