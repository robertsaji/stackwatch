"""Stack coverage tracking — measures what fraction of stacks are being monitored."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from stackwatch.drift import DriftResult


class CoverageError(Exception):
    """Raised when coverage calculation fails."""


@dataclass(frozen=True)
class CoverageReport:
    total_stacks: int
    monitored_stacks: int
    unmonitored_stacks: Sequence[str]

    @property
    def coverage_rate(self) -> float:
        if self.total_stacks == 0:
            return 0.0
        return self.monitored_stacks / self.total_stacks

    @property
    def coverage_pct(self) -> float:
        return round(self.coverage_rate * 100, 1)

    @property
    def is_full_coverage(self) -> bool:
        return self.monitored_stacks == self.total_stacks


def build_coverage_report(
    all_stack_names: Sequence[str],
    results: Sequence[DriftResult],
) -> CoverageReport:
    """Compare known stacks against monitored results to find gaps."""
    if not all_stack_names:
        return CoverageReport(
            total_stacks=0,
            monitored_stacks=0,
            unmonitored_stacks=[],
        )

    monitored = {r.stack_name for r in results}
    all_names = list(all_stack_names)
    unmonitored = [n for n in all_names if n not in monitored]

    return CoverageReport(
        total_stacks=len(all_names),
        monitored_stacks=len(monitored & set(all_names)),
        unmonitored_stacks=unmonitored,
    )


def render_coverage_text(report: CoverageReport) -> str:
    """Render a human-readable coverage summary."""
    lines = [
        f"Stack Coverage: {report.coverage_pct}% ({report.monitored_stacks}/{report.total_stacks})",
    ]
    if report.unmonitored_stacks:
        lines.append("Unmonitored stacks:")
        for name in sorted(report.unmonitored_stacks):
            lines.append(f"  - {name}")
    else:
        lines.append("All stacks are monitored.")
    return "\n".join(lines)
