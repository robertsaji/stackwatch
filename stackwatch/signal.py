"""Signal aggregation: combine multiple drift results into a single signal score."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackwatch.drift import DriftResult


@dataclass
class SignalConfig:
    """Weights used when computing the aggregate signal score."""
    drift_weight: float = 1.0
    severity_weight: float = 2.0
    recurrence_weight: float = 1.5

    def __post_init__(self) -> None:
        for attr in ("drift_weight", "severity_weight", "recurrence_weight"):
            v = getattr(self, attr)
            if v < 0:
                raise ValueError(f"{attr} must be >= 0, got {v}")


@dataclass
class StackSignal:
    stack_name: str
    score: float
    drifted_count: int
    total_count: int

    @property
    def label(self) -> str:
        if self.score >= 8.0:
            return "critical"
        if self.score >= 5.0:
            return "high"
        if self.score >= 2.0:
            return "medium"
        return "low"


@dataclass
class SignalReport:
    signals: List[StackSignal] = field(default_factory=list)

    @property
    def critical(self) -> List[StackSignal]:
        return [s for s in self.signals if s.label == "critical"]

    @property
    def high_or_above(self) -> List[StackSignal]:
        return [s for s in self.signals if s.label in ("high", "critical")]

    def top(self, n: int = 5) -> List[StackSignal]:
        return sorted(self.signals, key=lambda s: s.score, reverse=True)[:n]


def _score_result(result: DriftResult, cfg: SignalConfig, recurrence: int) -> float:
    """Compute a numeric signal score for a single DriftResult."""
    if not result.has_drift:
        return 0.0
    total = len(result.resources)
    drifted = sum(1 for r in result.resources if r.drift_status != "NOT_CHECKED")
    drift_fraction = drifted / total if total else 0.0
    base = drift_fraction * cfg.drift_weight * 10
    severity_bonus = (drifted / max(total, 1)) * cfg.severity_weight
    recurrence_bonus = min(recurrence, 5) * cfg.recurrence_weight * 0.5
    return round(base + severity_bonus + recurrence_bonus, 2)


def build_signal_report(
    results: List[DriftResult],
    cfg: SignalConfig | None = None,
    recurrence_map: dict[str, int] | None = None,
) -> SignalReport:
    """Build a SignalReport from a list of DriftResults."""
    cfg = cfg or SignalConfig()
    recurrence_map = recurrence_map or {}
    signals = []
    for result in results:
        recurrence = recurrence_map.get(result.stack_name, 0)
        score = _score_result(result, cfg, recurrence)
        total = len(result.resources)
        drifted = sum(1 for r in result.resources if r.drift_status != "NOT_CHECKED")
        signals.append(StackSignal(
            stack_name=result.stack_name,
            score=score,
            drifted_count=drifted,
            total_count=total,
        ))
    return SignalReport(signals=signals)


def render_signal_text(report: SignalReport) -> str:
    lines = ["Signal Report", "============="]
    for sig in sorted(report.signals, key=lambda s: s.score, reverse=True):
        lines.append(f"  [{sig.label.upper():8s}] {sig.stack_name}  score={sig.score}")
    if not report.signals:
        lines.append("  (no stacks)")
    return "\n".join(lines)
