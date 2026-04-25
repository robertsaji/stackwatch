"""Recheck module: selectively re-run drift detection on stacks that were
drifted in the most recent snapshot, avoiding full scans when only targeted
re-verification is needed."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.drift import DriftDetector, DriftResult
from stackwatch.snapshot import Snapshot


@dataclass
class RecheckConfig:
    """Configuration for selective recheck runs."""
    only_drifted: bool = True          # when True, only recheck previously drifted stacks
    max_stacks: Optional[int] = None   # cap the number of stacks rechecked per run

    def __post_init__(self) -> None:
        if self.max_stacks is not None and self.max_stacks < 1:
            raise ValueError("max_stacks must be a positive integer")


@dataclass
class RecheckReport:
    """Result of a recheck run."""
    rechecked: List[DriftResult] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

    @property
    def total_rechecked(self) -> int:
        return len(self.rechecked)

    @property
    def still_drifted(self) -> int:
        return sum(1 for r in self.rechecked if r.drifted)

    @property
    def resolved(self) -> int:
        return sum(1 for r in self.rechecked if not r.drifted)


def build_recheck_targets(
    snapshot: Snapshot,
    cfg: RecheckConfig,
) -> List[str]:
    """Return the list of stack names to recheck based on the snapshot and config."""
    if cfg.only_drifted:
        targets = list(snapshot.drifted)
    else:
        targets = list(snapshot.stack_names)

    if cfg.max_stacks is not None:
        targets = targets[: cfg.max_stacks]

    return targets


def run_recheck(
    snapshot: Snapshot,
    detector: DriftDetector,
    cfg: Optional[RecheckConfig] = None,
) -> RecheckReport:
    """Re-run drift detection for the selected stacks and return a RecheckReport."""
    if cfg is None:
        cfg = RecheckConfig()

    targets = build_recheck_targets(snapshot, cfg)
    skipped = [s for s in snapshot.stack_names if s not in targets]

    results: List[DriftResult] = []
    for stack_name in targets:
        result = detector.detect(stack_name)
        results.append(result)

    return RecheckReport(rechecked=results, skipped=skipped)


def render_recheck_text(report: RecheckReport) -> str:
    """Render a human-readable summary of a RecheckReport."""
    lines = [
        f"Recheck summary: {report.total_rechecked} stack(s) rechecked, "
        f"{report.still_drifted} still drifted, {report.resolved} resolved.",
    ]
    for result in report.rechecked:
        status = "DRIFTED" if result.drifted else "IN SYNC"
        lines.append(f"  [{status}] {result.stack_name}")
    if report.skipped:
        lines.append(f"Skipped ({len(report.skipped)}): {', '.join(report.skipped)}")
    return "\n".join(lines)
