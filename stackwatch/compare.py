"""Compare two drift snapshots and produce a diff report."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set
from stackwatch.snapshot import Snapshot


@dataclass
class CompareReport:
    newly_drifted: List[str] = field(default_factory=list)
    resolved: List[str] = field(default_factory=list)
    still_drifted: List[str] = field(default_factory=list)
    unchanged_clean: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.newly_drifted or self.resolved)


def compare_snapshots(before: Snapshot, after: Snapshot) -> CompareReport:
    before_drifted: Set[str] = set(before.drifted())
    after_drifted: Set[str] = set(after.drifted())
    all_stacks: Set[str] = set(before.stack_names()) | set(after.stack_names())

    newly_drifted = sorted(after_drifted - before_drifted)
    resolved = sorted(before_drifted - after_drifted)
    still_drifted = sorted(before_drifted & after_drifted)
    unchanged_clean = sorted(all_stacks - before_drifted - after_drifted)

    return CompareReport(
        newly_drifted=newly_drifted,
        resolved=resolved,
        still_drifted=still_drifted,
        unchanged_clean=unchanged_clean,
    )


def render_compare_text(report: CompareReport) -> str:
    lines = ["=== Snapshot Comparison ==="]
    if not report.has_changes:
        lines.append("No changes between snapshots.")
    if report.newly_drifted:
        lines.append(f"\nNewly drifted ({len(report.newly_drifted)}):")
        for s in report.newly_drifted:
            lines.append(f"  [+] {s}")
    if report.resolved:
        lines.append(f"\nResolved ({len(report.resolved)}):")
        for s in report.resolved:
            lines.append(f"  [-] {s}")
    if report.still_drifted:
        lines.append(f"\nStill drifted ({len(report.still_drifted)}):")
        for s in report.still_drifted:
            lines.append(f"  [~] {s}")
    return "\n".join(lines)
