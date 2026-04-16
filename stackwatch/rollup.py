"""Rollup: aggregate drift results across multiple runs into a period summary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackwatch.drift import DriftResult


@dataclass
class RollupEntry:
    stack_name: str
    total_checks: int
    drifted_checks: int

    @property
    def drift_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.drifted_checks / self.total_checks


@dataclass
class RollupReport:
    entries: List[RollupEntry] = field(default_factory=list)

    @property
    def total_stacks(self) -> int:
        return len(self.entries)

    @property
    def always_drifted(self) -> List[RollupEntry]:
        return [e for e in self.entries if e.drift_rate == 1.0]

    @property
    def never_drifted(self) -> List[RollupEntry]:
        return [e for e in self.entries if e.drift_rate == 0.0]


def build_rollup(runs: List[List[DriftResult]]) -> RollupReport:
    """Build a rollup report from a list of runs, each run being a list of DriftResults."""
    counts: dict[str, dict] = {}
    for run in runs:
        for result in run:
            entry = counts.setdefault(result.stack_name, {"total": 0, "drifted": 0})
            entry["total"] += 1
            if result.has_drift:
                entry["drifted"] += 1
    entries = [
        RollupEntry(stack_name=name, total_checks=v["total"], drifted_checks=v["drifted"])
        for name, v in sorted(counts.items())
    ]
    return RollupReport(entries=entries)


def render_rollup_text(report: RollupReport) -> str:
    if not report.entries:
        return "No data in rollup."
    lines = ["Rollup Report", "=" * 40]
    for e in report.entries:
        lines.append(f"{e.stack_name}: {e.drifted_checks}/{e.total_checks} drifted ({e.drift_rate:.0%})")
    lines.append("=" * 40)
    lines.append(f"Always drifted: {len(report.always_drifted)}  Never drifted: {len(report.never_drifted)}")
    return "\n".join(lines)
