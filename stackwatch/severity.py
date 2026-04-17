"""Drift severity classification for CloudFormation stacks."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List

from stackwatch.drift import DriftResult


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SeverityResult:
    stack_name: str
    level: SeverityLevel
    drifted_count: int
    total_count: int

    @property
    def label(self) -> str:
        return self.level.value.upper()


def classify(result: DriftResult) -> SeverityResult:
    """Classify drift severity based on number of drifted resources."""
    if not result.has_drift:
        level = SeverityLevel.LOW
    else:
        drifted = len([r for r in result.resources if r.drifted])
        total = len(result.resources)
        ratio = drifted / total if total else 0.0
        if ratio >= 0.75:
            level = SeverityLevel.CRITICAL
        elif ratio >= 0.5:
            level = SeverityLevel.HIGH
        elif ratio >= 0.25:
            level = SeverityLevel.MEDIUM
        else:
            level = SeverityLevel.LOW
        drifted_count = drifted
        return SeverityResult(
            stack_name=result.stack_name,
            level=level,
            drifted_count=drifted,
            total_count=total,
        )
    return SeverityResult(
        stack_name=result.stack_name,
        level=level,
        drifted_count=0,
        total_count=len(result.resources),
    )


def classify_all(results: List[DriftResult]) -> List[SeverityResult]:
    return [classify(r) for r in results]


def render_severity_text(results: List[SeverityResult]) -> str:
    lines = ["Severity Report", "=" * 40]
    for r in results:
        lines.append(f"[{r.label}] {r.stack_name} — {r.drifted_count}/{r.total_count} resources drifted")
    if not results:
        lines.append("No results.")
    return "\n".join(lines)
