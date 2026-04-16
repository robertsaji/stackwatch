"""Cost-aware drift alerting: skip alerts for stacks below a cost threshold."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from stackwatch.drift import DriftResult


@dataclass
class CostAlertConfig:
    min_monthly_cost: float = 0.0  # USD; stacks below this are skipped
    stack_costs: Dict[str, float] = field(default_factory=dict)  # stack_name -> monthly USD

    def __post_init__(self) -> None:
        if self.min_monthly_cost < 0:
            raise ValueError("min_monthly_cost must be >= 0")


@dataclass
class CostAlertResult:
    result: DriftResult
    cost: Optional[float]
    suppressed: bool
    reason: str = ""


class CostAlertFilter:
    def __init__(self, config: CostAlertConfig) -> None:
        self._config = config

    def evaluate(self, result: DriftResult) -> CostAlertResult:
        """Return a CostAlertResult indicating whether the alert should fire."""
        if not result.has_drift:
            return CostAlertResult(result=result, cost=None, suppressed=True, reason="no drift")

        cost = self._config.stack_costs.get(result.stack_name)
        threshold = self._config.min_monthly_cost

        if threshold > 0 and (cost is None or cost < threshold):
            reason = (
                f"cost ${cost:.2f} below threshold ${threshold:.2f}"
                if cost is not None
                else f"cost unknown, threshold ${threshold:.2f}"
            )
            return CostAlertResult(result=result, cost=cost, suppressed=True, reason=reason)

        return CostAlertResult(result=result, cost=cost, suppressed=False)

    def apply(self, results: list[DriftResult]) -> list[CostAlertResult]:
        return [self.evaluate(r) for r in results]
