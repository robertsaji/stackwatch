"""Drift trend analysis over historical entries."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from stackwatch.history import HistoryEntry


@dataclass
class TrendPoint:
    timestamp: str
    total_stacks: int
    drifted_stacks: int

    @property
    def drift_rate(self) -> float:
        if self.total_stacks == 0:
            return 0.0
        return self.drifted_stacks / self.total_stacks


@dataclass
class TrendReport:
    points: List[TrendPoint]

    @property
    def improving(self) -> bool:
        rates = [p.drift_rate for p in self.points]
        if len(rates) < 2:
            return False
        return rates[-1] < rates[0]

    @property
    def worsening(self) -> bool:
        rates = [p.drift_rate for p in self.points]
        if len(rates) < 2:
            return False
        return rates[-1] > rates[0]


def build_trend(entries: List[HistoryEntry]) -> TrendReport:
    points: List[TrendPoint] = []
    for entry in entries:
        drifted = sum(1 for r in entry.results if r.has_drift)
        points.append(TrendPoint(
            timestamp=entry.timestamp,
            total_stacks=len(entry.results),
            drifted_stacks=drifted,
        ))
    return TrendReport(points=points)


def render_trend_text(report: TrendReport) -> str:
    if not report.points:
        return "No trend data available."
    lines = ["Drift Trend:", "-" * 40]
    for p in report.points:
        lines.append(f"  {p.timestamp}  drifted={p.drifted_stacks}/{p.total_stacks}  rate={p.drift_rate:.0%}")
    if report.improving:
        lines.append("Trend: IMPROVING")
    elif report.worsening:
        lines.append("Trend: WORSENING")
    else:
        lines.append("Trend: STABLE")
    return "\n".join(lines)
