"""Budget-aware drift alerting: suppress or flag results based on estimated remediation cost thresholds."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.drift import DriftResult


class BudgetError(Exception):
    """Raised when budget configuration is invalid."""


@dataclass
class BudgetConfig:
    """Configuration for budget-aware filtering."""

    cost_per_drifted_resource: float = 5.0  # estimated USD per drifted resource
    monthly_budget: float = 500.0           # USD
    warn_threshold: float = 0.80            # fraction of budget to trigger a warning

    def __post_init__(self) -> None:
        if self.cost_per_drifted_resource < 0:
            raise BudgetError("cost_per_drifted_resource must be >= 0")
        if self.monthly_budget <= 0:
            raise BudgetError("monthly_budget must be > 0")
        if not (0 < self.warn_threshold <= 1.0):
            raise BudgetError("warn_threshold must be between 0 (exclusive) and 1 (inclusive)")


@dataclass
class BudgetResult:
    """Outcome of a budget check for a set of drift results."""

    estimated_cost: float
    monthly_budget: float
    warn_threshold: float
    over_budget: bool
    near_budget: bool
    drifted_resource_count: int

    @property
    def budget_used_fraction(self) -> float:
        return self.estimated_cost / self.monthly_budget if self.monthly_budget else 0.0

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.monthly_budget - self.estimated_cost)


def _count_drifted_resources(results: List[DriftResult]) -> int:
    return sum(
        len(r.drifted_resources)
        for r in results
        if r.has_drift
    )


def check_budget(results: List[DriftResult], config: Optional[BudgetConfig] = None) -> BudgetResult:
    """Estimate remediation cost for *results* and compare against the configured budget."""
    if config is None:
        config = BudgetConfig()

    count = _count_drifted_resources(results)
    estimated = count * config.cost_per_drifted_resource
    over = estimated > config.monthly_budget
    near = (not over) and (estimated / config.monthly_budget) >= config.warn_threshold

    return BudgetResult(
        estimated_cost=estimated,
        monthly_budget=config.monthly_budget,
        warn_threshold=config.warn_threshold,
        over_budget=over,
        near_budget=near,
        drifted_resource_count=count,
    )


def render_budget_text(result: BudgetResult) -> str:
    """Return a human-readable summary of the budget check."""
    lines = [
        f"Drifted resources : {result.drifted_resource_count}",
        f"Estimated cost    : ${result.estimated_cost:,.2f}",
        f"Monthly budget    : ${result.monthly_budget:,.2f}",
        f"Budget remaining  : ${result.budget_remaining:,.2f}",
        f"Budget used       : {result.budget_used_fraction * 100:.1f}%",
    ]
    if result.over_budget:
        lines.append("Status            : OVER BUDGET")
    elif result.near_budget:
        lines.append("Status            : WARNING — approaching budget limit")
    else:
        lines.append("Status            : OK")
    return "\n".join(lines)
