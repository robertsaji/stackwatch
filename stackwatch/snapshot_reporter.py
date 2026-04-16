"""Renders a human-readable diff between two snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from stackwatch.drift import DriftResult
from stackwatch.snapshot import DriftSnapshot


@dataclass
class SnapshotDiffReport:
    new: List[str]
    drifted: List[str]
    resolved: List[str]

    @property
    def has_changes(self) -> bool:
        return bool(self.new or self.drifted or self.resolved)


def build_diff_report(snapshot: DriftSnapshot, current: List[DriftResult]) -> SnapshotDiffReport:
    changes: Dict[str, str] = snapshot.diff(current)
    new, drifted, resolved = [], [], []
    for stack, change in changes.items():
        if change == "new":
            new.append(stack)
        elif change == "drifted":
            drifted.append(stack)
        elif change == "resolved":
            resolved.append(stack)
    return SnapshotDiffReport(new=sorted(new), drifted=sorted(drifted), resolved=sorted(resolved))


def render_diff_text(report: SnapshotDiffReport) -> str:
    if not report.has_changes:
        return "No drift status changes since last snapshot.\n"

    lines: List[str] = ["Drift Status Changes\n", "=" * 40 + "\n"]

    if report.drifted:
        lines.append("Newly Drifted:\n")
        for name in report.drifted:
            lines.append(f"  [!] {name}\n")

    if report.resolved:
        lines.append("Resolved:\n")
        for name in report.resolved:
            lines.append(f"  [✓] {name}\n")

    if report.new:
        lines.append("New Stacks:\n")
        for name in report.new:
            lines.append(f"  [+] {name}\n")

    return "".join(lines)
