"""Drift scoring module — assigns a numeric risk score to drift results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackwatch.drift import DriftResult

# Weight per drifted resource
_RESOURCE_WEIGHT = 10
# Bonus penalty when more than half the stack's resources are drifted
_MAJORITY_PENALTY = 25
# Maximum score cap
_MAX_SCORE = 100


@dataclass(frozen=True)
class StackScore:
    stack_name: str
    score: int          # 0–100
    drifted_count: int
    total_resources: int
    label: str          # LOW / MEDIUM / HIGH / CRITICAL


@dataclass(frozen=True)
class ScoringReport:
    scores: List[StackScore] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores) / len(self.scores)

    @property
    def highest_score(self) -> StackScore | None:
        return max(self.scores, key=lambda s: s.score, default=None)


def _label(score: int) -> str:
    if score == 0:
        return "LOW"
    if score < 30:
        return "LOW"
    if score < 60:
        return "MEDIUM"
    if score < 85:
        return "HIGH"
    return "CRITICAL"


def score_result(result: DriftResult) -> StackScore:
    """Compute a risk score for a single DriftResult."""
    drifted = len(result.drifted_resources)
    total = max(drifted, 1)  # guard; real total unknown without extra API call

    raw = drifted * _RESOURCE_WEIGHT
    if drifted > total // 2:
        raw += _MAJORITY_PENALTY
    score = min(raw, _MAX_SCORE)
    return StackScore(
        stack_name=result.stack_name,
        score=score,
        drifted_count=drifted,
        total_resources=total,
        label=_label(score),
    )


def build_scoring_report(results: List[DriftResult]) -> ScoringReport:
    """Score all results and return a ScoringReport."""
    return ScoringReport(scores=[score_result(r) for r in results])


def render_scoring_text(report: ScoringReport) -> str:
    """Render a human-readable scoring report."""
    if not report.scores:
        return "No stacks scored."
    lines = ["Drift Risk Scores", "=" * 40]
    for s in sorted(report.scores, key=lambda x: x.score, reverse=True):
        lines.append(f"  {s.stack_name:<40} {s.score:>3}/100  [{s.label}]")
    lines.append("-" * 40)
    lines.append(f"  Average score: {report.average_score:.1f}")
    return "\n".join(lines)
