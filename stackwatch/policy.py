"""Drift policy enforcement: fail or warn based on drift thresholds."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackwatch.drift import DriftResult


class PolicyError(Exception):
    pass


@dataclass
class PolicyConfig:
    max_drifted_stacks: int = 0          # 0 = any drift fails
    max_drift_rate: float = 0.0          # 0.0 = any drift fails
    warn_only: bool = False

    def __post_init__(self) -> None:
        if self.max_drifted_stacks < 0:
            raise PolicyError("max_drifted_stacks must be >= 0")
        if not (0.0 <= self.max_drift_rate <= 1.0):
            raise PolicyError("max_drift_rate must be between 0.0 and 1.0")


@dataclass
class PolicyViolation:
    stack_name: str
    reason: str


@dataclass
class PolicyResult:
    violations: List[PolicyViolation] = field(default_factory=list)
    warn_only: bool = False

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    @property
    def should_fail(self) -> bool:
        return not self.passed and not self.warn_only

    def render_text(self) -> str:
        if self.passed:
            return "Policy check passed. No violations."
        lines = ["Policy violations detected:"]
        for v in self.violations:
            prefix = "[WARN]" if self.warn_only else "[FAIL]"
            lines.append(f"  {prefix} {v.stack_name}: {v.reason}")
        return "\n".join(lines)


def evaluate_policy(results: List[DriftResult], config: PolicyConfig) -> PolicyResult:
    """Evaluate drift results against the given policy configuration."""
    drifted = [r for r in results if r.has_drift]
    violations: List[PolicyViolation] = []

    if results:
        rate = len(drifted) / len(results)
        if rate > config.max_drift_rate:
            for r in drifted:
                violations.append(
                    PolicyViolation(
                        stack_name=r.stack_name,
                        reason=(
                            f"drift rate {rate:.0%} exceeds allowed "
                            f"{config.max_drift_rate:.0%}"
                        ),
                    )
                )

    if len(drifted) > config.max_drifted_stacks and not violations:
        for r in drifted:
            violations.append(
                PolicyViolation(
                    stack_name=r.stack_name,
                    reason=(
                        f"drifted stacks ({len(drifted)}) exceed allowed "
                        f"{config.max_drifted_stacks}"
                    ),
                )
            )

    return PolicyResult(violations=violations, warn_only=config.warn_only)
