"""TTL (time-to-live) enforcement for drift results.

Allows callers to mark a DriftResult as "fresh" or "stale" based on
how long ago it was detected, and to filter out results that have
exceeded a configurable TTL.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from stackwatch.drift import DriftResult


class TTLError(Exception):
    """Raised when TTL configuration is invalid."""


@dataclass
class TTLConfig:
    max_age_seconds: int = 3600  # 1 hour default

    def __post_init__(self) -> None:
        if self.max_age_seconds <= 0:
            raise TTLError(
                f"max_age_seconds must be positive, got {self.max_age_seconds}"
            )


@dataclass
class TTLResult:
    result: DriftResult
    detected_at: datetime
    is_fresh: bool

    @property
    def age_seconds(self) -> float:
        now = datetime.now(tz=timezone.utc)
        detected = self.detected_at
        if detected.tzinfo is None:
            detected = detected.replace(tzinfo=timezone.utc)
        return (now - detected).total_seconds()


@dataclass
class TTLReport:
    entries: List[TTLResult] = field(default_factory=list)

    @property
    def fresh(self) -> List[TTLResult]:
        return [e for e in self.entries if e.is_fresh]

    @property
    def stale(self) -> List[TTLResult]:
        return [e for e in self.entries if not e.is_fresh]


def apply_ttl(
    results: List[DriftResult],
    detected_at_map: dict,
    config: TTLConfig | None = None,
) -> TTLReport:
    """Classify each result as fresh or stale.

    Args:
        results: List of DriftResult objects to evaluate.
        detected_at_map: Mapping of stack_name -> datetime when drift was detected.
        config: TTLConfig controlling max age; defaults to TTLConfig().

    Returns:
        TTLReport with all results annotated.
    """
    if config is None:
        config = TTLConfig()

    entries: List[TTLResult] = []
    now = datetime.now(tz=timezone.utc)

    for result in results:
        detected = detected_at_map.get(result.stack_name, now)
        if detected.tzinfo is None:
            detected = detected.replace(tzinfo=timezone.utc)
        age = (now - detected).total_seconds()
        entries.append(
            TTLResult(
                result=result,
                detected_at=detected,
                is_fresh=age <= config.max_age_seconds,
            )
        )

    return TTLReport(entries=entries)


def render_ttl_text(report: TTLReport) -> str:
    lines = [
        f"TTL Report — {len(report.fresh)} fresh / {len(report.stale)} stale",
        "-" * 50,
    ]
    for entry in report.entries:
        status = "FRESH" if entry.is_fresh else "STALE"
        lines.append(
            f"  [{status}] {entry.result.stack_name}  "
            f"(age {entry.age_seconds:.0f}s)"
        )
    return "\n".join(lines)
