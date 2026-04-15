"""Summary module: aggregates drift results into a concise summary report."""
from dataclasses import dataclass, field
from typing import List

from stackwatch.drift import DriftResult


@dataclass
class StackSummary:
    stack_name: str
    status: str  # 'DRIFTED' | 'IN_SYNC' | 'NOT_CHECKED'
    drifted_resource_count: int = 0
    resource_types: List[str] = field(default_factory=list)


@dataclass
class RunSummary:
    total_stacks: int = 0
    drifted_stacks: int = 0
    in_sync_stacks: int = 0
    total_drifted_resources: int = 0
    stacks: List[StackSummary] = field(default_factory=list)

    @property
    def drift_rate(self) -> float:
        """Fraction of stacks that have drifted (0.0 – 1.0)."""
        if self.total_stacks == 0:
            return 0.0
        return self.drifted_stacks / self.total_stacks


def build_summary(results: List[DriftResult]) -> RunSummary:
    """Build a :class:`RunSummary` from a list of drift detection results."""
    summary = RunSummary(total_stacks=len(results))

    for result in results:
        resource_types = list(
            {r.resource_type for r in result.drifted_resources}
        )
        stack_summary = StackSummary(
            stack_name=result.stack_name,
            status=result.status,
            drifted_resource_count=len(result.drifted_resources),
            resource_types=sorted(resource_types),
        )
        summary.stacks.append(stack_summary)

        if result.status == "DRIFTED":
            summary.drifted_stacks += 1
            summary.total_drifted_resources += len(result.drifted_resources)
        else:
            summary.in_sync_stacks += 1

    return summary


def render_summary_text(summary: RunSummary) -> str:
    """Render a plain-text representation of *summary*."""
    lines = [
        f"Stacks checked : {summary.total_stacks}",
        f"Drifted        : {summary.drifted_stacks}",
        f"In sync        : {summary.in_sync_stacks}",
        f"Drift rate     : {summary.drift_rate:.0%}",
        f"Drifted res.   : {summary.total_drifted_resources}",
        "",
    ]
    for s in summary.stacks:
        marker = "[DRIFT]" if s.status == "DRIFTED" else "[OK]   "
        line = f"  {marker} {s.stack_name}"
        if s.drifted_resource_count:
            types = ", ".join(s.resource_types)
            line += f" — {s.drifted_resource_count} resource(s): {types}"
        lines.append(line)
    return "\n".join(lines)
