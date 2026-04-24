"""Drift forecasting module.

Uses historical drift data to project future drift likelihood for each stack,
based on observed drift frequency over a rolling window.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.history import HistoryEntry


@dataclass
class ForecastConfig:
    """Configuration for the drift forecaster."""

    # Number of most-recent history entries to consider per stack
    window_size: int = 10
    # Probability threshold above which a stack is considered "at risk"
    risk_threshold: float = 0.5

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")
        if not (0.0 <= self.risk_threshold <= 1.0):
            raise ValueError("risk_threshold must be between 0.0 and 1.0")


@dataclass
class StackForecast:
    """Drift forecast for a single stack."""

    stack_name: str
    # Estimated probability of drift on the next check (0.0 – 1.0)
    drift_probability: float
    # Number of history points used to compute the estimate
    sample_size: int
    # Human-readable risk label
    risk_label: str


@dataclass
class ForecastReport:
    """Aggregated forecast across all monitored stacks."""

    forecasts: List[StackForecast] = field(default_factory=list)
    config: ForecastConfig = field(default_factory=ForecastConfig)

    @property
    def at_risk(self) -> List[StackForecast]:
        """Return stacks whose drift probability exceeds the configured threshold."""
        return [
            f for f in self.forecasts
            if f.drift_probability >= self.config.risk_threshold
        ]

    @property
    def total_stacks(self) -> int:
        return len(self.forecasts)

    @property
    def at_risk_count(self) -> int:
        return len(self.at_risk)


def _risk_label(probability: float) -> str:
    """Map a probability value to a human-readable risk label."""
    if probability >= 0.75:
        return "HIGH"
    if probability >= 0.5:
        return "MEDIUM"
    if probability >= 0.25:
        return "LOW"
    return "MINIMAL"


def _estimate_probability(entries: List[HistoryEntry], window: int) -> tuple[float, int]:
    """Estimate drift probability from the most recent *window* entries.

    Returns a (probability, sample_size) tuple.  Uses Laplace smoothing
    (add-one) so that stacks with very little history still return a
    meaningful estimate rather than 0 or 1.
    """
    recent = entries[-window:] if len(entries) > window else entries
    sample_size = len(recent)
    if sample_size == 0:
        return 0.0, 0

    drifted_count = sum(1 for e in recent if e.has_drift)
    # Laplace (add-one) smoothing
    probability = (drifted_count + 1) / (sample_size + 2)
    return round(probability, 4), sample_size


def build_forecast(
    history_by_stack: dict[str, List[HistoryEntry]],
    config: Optional[ForecastConfig] = None,
) -> ForecastReport:
    """Build a :class:`ForecastReport` from per-stack history.

    Args:
        history_by_stack: Mapping of stack name → list of :class:`HistoryEntry`
            objects ordered oldest-first.
        config: Optional forecasting configuration; defaults are used when
            *None* is passed.

    Returns:
        A :class:`ForecastReport` containing a :class:`StackForecast` for
        every stack present in *history_by_stack*.
    """
    cfg = config or ForecastConfig()
    forecasts: List[StackForecast] = []

    for stack_name, entries in sorted(history_by_stack.items()):
        probability, sample_size = _estimate_probability(entries, cfg.window_size)
        forecasts.append(
            StackForecast(
                stack_name=stack_name,
                drift_probability=probability,
                sample_size=sample_size,
                risk_label=_risk_label(probability),
            )
        )

    return ForecastReport(forecasts=forecasts, config=cfg)


def render_forecast_text(report: ForecastReport) -> str:
    """Render a plain-text summary of the forecast report."""
    lines: List[str] = [
        "Drift Forecast Report",
        "=" * 40,
        f"Stacks analysed : {report.total_stacks}",
        f"At-risk stacks  : {report.at_risk_count} "
        f"(threshold ≥ {report.config.risk_threshold:.0%})",
        "",
    ]

    if not report.forecasts:
        lines.append("No forecast data available.")
        return "\n".join(lines)

    lines.append(f"{'Stack':<40} {'Prob':>6}  {'Risk':<8}  {'Samples':>7}")
    lines.append("-" * 68)
    for fc in sorted(report.forecasts, key=lambda x: x.drift_probability, reverse=True):
        lines.append(
            f"{fc.stack_name:<40} {fc.drift_probability:>6.1%}  "
            f"{fc.risk_label:<8}  {fc.sample_size:>7}"
        )

    return "\n".join(lines)
