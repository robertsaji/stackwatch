"""Drift heatmap: aggregates drift frequency per stack over a history window."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from stackwatch.history import HistoryEntry


@dataclass
class HeatmapCell:
    stack_name: str
    total_checks: int
    drifted_checks: int

    @property
    def drift_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.drifted_checks / self.total_checks

    @property
    def heat_label(self) -> str:
        rate = self.drift_rate
        if rate == 0.0:
            return "none"
        if rate < 0.25:
            return "low"
        if rate < 0.60:
            return "medium"
        if rate < 0.85:
            return "high"
        return "critical"


@dataclass
class Heatmap:
    cells: List[HeatmapCell] = field(default_factory=list)

    @property
    def total_stacks(self) -> int:
        return len(self.cells)

    def hottest(self, n: int = 5) -> List[HeatmapCell]:
        return sorted(self.cells, key=lambda c: c.drift_rate, reverse=True)[:n]


def build_heatmap(entries: List[HistoryEntry]) -> Heatmap:
    """Build a heatmap from a list of history entries."""
    totals: Dict[str, int] = {}
    drifted: Dict[str, int] = {}

    for entry in entries:
        name = entry.stack_name
        totals[name] = totals.get(name, 0) + 1
        if entry.drifted:
            drifted[name] = drifted.get(name, 0) + 1

    cells = [
        HeatmapCell(
            stack_name=name,
            total_checks=totals[name],
            drifted_checks=drifted.get(name, 0),
        )
        for name in totals
    ]
    cells.sort(key=lambda c: c.stack_name)
    return Heatmap(cells=cells)


def render_heatmap_text(heatmap: Heatmap) -> str:
    """Render the heatmap as a plain-text table."""
    if not heatmap.cells:
        return "No heatmap data available."

    lines = [
        f"{'Stack':<40} {'Checks':>7} {'Drifted':>8} {'Rate':>7} {'Heat':<8}",
        "-" * 76,
    ]
    for cell in heatmap.cells:
        lines.append(
            f"{cell.stack_name:<40} {cell.total_checks:>7} "
            f"{cell.drifted_checks:>8} {cell.drift_rate:>6.1%} {cell.heat_label:<8}"
        )
    return "\n".join(lines)
