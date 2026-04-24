"""Stale drift detection — flags stacks whose drift check is overdue."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from stackwatch.drift import DriftResult
from stackwatch.history import HistoryEntry


class StaleError(Exception):
    """Raised when stale detection is misconfigured."""


@dataclass
class StaleConfig:
    max_age_hours: float = 24.0

    def __post_init__(self) -> None:
        if self.max_age_hours <= 0:
            raise StaleError("max_age_hours must be positive")


@dataclass
class StaleResult:
    stack_name: str
    last_checked: Optional[datetime]
    age_hours: Optional[float]
    is_stale: bool


@dataclass
class StaleReport:
    stale: List[StaleResult] = field(default_factory=list)
    fresh: List[StaleResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.stale) + len(self.fresh)

    @property
    def stale_count(self) -> int:
        return len(self.stale)


def _age_hours(ts: datetime) -> float:
    now = datetime.now(tz=timezone.utc)
    delta = now - ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else now - ts
    return delta.total_seconds() / 3600.0


def build_stale_report(
    results: List[DriftResult],
    history: List[HistoryEntry],
    config: Optional[StaleConfig] = None,
) -> StaleReport:
    """Cross-reference current stacks with history to find stale checks."""
    if config is None:
        config = StaleConfig()

    last_seen: dict[str, datetime] = {}
    for entry in history:
        ts = entry.timestamp
        if entry.stack_name not in last_seen or ts > last_seen[entry.stack_name]:
            last_seen[entry.stack_name] = ts

    report = StaleReport()
    for result in results:
        name = result.stack_name
        ts = last_seen.get(name)
        if ts is None:
            sr = StaleResult(stack_name=name, last_checked=None, age_hours=None, is_stale=True)
        else:
            age = _age_hours(ts)
            sr = StaleResult(stack_name=name, last_checked=ts, age_hours=round(age, 2), is_stale=age > config.max_age_hours)
        if sr.is_stale:
            report.stale.append(sr)
        else:
            report.fresh.append(sr)
    return report


def render_stale_text(report: StaleReport) -> str:
    lines = [f"Stale Report — {report.stale_count}/{report.total} stacks overdue"]
    for sr in report.stale:
        age_str = f"{sr.age_hours:.1f}h ago" if sr.age_hours is not None else "never checked"
        lines.append(f"  [STALE] {sr.stack_name} ({age_str})")
    for sr in report.fresh:
        lines.append(f"  [OK]    {sr.stack_name} ({sr.age_hours:.1f}h ago)")
    return "\n".join(lines)
