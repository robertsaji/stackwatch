"""Drift anomaly detection: flag stacks whose drift rate deviates from historical baseline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from stackwatch.drift import DriftResult
from stackwatch.trend import TrendPoint


@dataclass
class AnomalyConfig:
    min_points: int = 3
    z_score_threshold: float = 2.0

    def __post_init__(self) -> None:
        if self.min_points < 1:
            raise ValueError("min_points must be >= 1")
        if self.z_score_threshold <= 0:
            raise ValueError("z_score_threshold must be positive")


@dataclass
class AnomalyResult:
    stack_name: str
    current_rate: float
    mean_rate: float
    std_rate: float
    z_score: float
    is_anomaly: bool


def _mean(values: List[float]) -> float:
    return sum(values) / len(values)


def _std(values: List[float], mean: float) -> float:
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def detect_anomaly(
    stack_name: str,
    history: List[TrendPoint],
    current_result: DriftResult,
    config: Optional[AnomalyConfig] = None,
) -> AnomalyResult:
    """Compare current drift rate against historical trend points."""
    cfg = config or AnomalyConfig()
    current_rate = 1.0 if current_result.has_drift else 0.0

    if len(history) < cfg.min_points:
        return AnomalyResult(
            stack_name=stack_name,
            current_rate=current_rate,
            mean_rate=0.0,
            std_rate=0.0,
            z_score=0.0,
            is_anomaly=False,
        )

    rates = [p.drift_rate for p in history]
    mean = _mean(rates)
    std = _std(rates, mean)

    if std == 0.0:
        z_score = 0.0
    else:
        z_score = abs(current_rate - mean) / std

    return AnomalyResult(
        stack_name=stack_name,
        current_rate=current_rate,
        mean_rate=mean,
        std_rate=std,
        z_score=z_score,
        is_anomaly=z_score >= cfg.z_score_threshold,
    )


def detect_anomalies(
    results: List[DriftResult],
    history_map: dict,
    config: Optional[AnomalyConfig] = None,
) -> List[AnomalyResult]:
    """Run anomaly detection for a list of drift results."""
    return [
        detect_anomaly(r.stack_name, history_map.get(r.stack_name, []), r, config)
        for r in results
    ]
