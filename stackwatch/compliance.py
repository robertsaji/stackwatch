"""Compliance checking: evaluate drift results against compliance standards."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.drift import DriftResult


class ComplianceError(Exception):
    """Raised for invalid compliance configuration."""


@dataclass
class ComplianceConfig:
    max_drifted_pct: float = 0.0  # 0.0 = zero tolerance
    required_tags: List[str] = field(default_factory=list)
    exempt_stacks: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (0.0 <= self.max_drifted_pct <= 100.0):
            raise ComplianceError(
                f"max_drifted_pct must be between 0 and 100, got {self.max_drifted_pct}"
            )


@dataclass
class ComplianceViolation:
    stack_name: str
    reason: str


@dataclass
class ComplianceResult:
    config: ComplianceConfig
    total_stacks: int
    drifted_stacks: int
    violations: List[ComplianceViolation]
    exempt_stacks: List[str]

    @property
    def is_compliant(self) -> bool:
        return len(self.violations) == 0

    @property
    def drifted_pct(self) -> float:
        if self.total_stacks == 0:
            return 0.0
        return (self.drifted_stacks / self.total_stacks) * 100.0


def check_compliance(
    results: List[DriftResult],
    config: Optional[ComplianceConfig] = None,
) -> ComplianceResult:
    """Evaluate a list of DriftResults against the given ComplianceConfig."""
    if config is None:
        config = ComplianceConfig()

    exempt = set(config.exempt_stacks)
    applicable = [r for r in results if r.stack_name not in exempt]
    drifted = [r for r in applicable if r.has_drift]

    violations: List[ComplianceViolation] = []
    for r in drifted:
        drifted_pct = (len(drifted) / len(applicable) * 100.0) if applicable else 0.0
        if drifted_pct > config.max_drifted_pct:
            violations.append(
                ComplianceViolation(
                    stack_name=r.stack_name,
                    reason=(
                        f"Stack has drift; drifted percentage {drifted_pct:.1f}% "
                        f"exceeds allowed {config.max_drifted_pct:.1f}%"
                    ),
                )
            )

    return ComplianceResult(
        config=config,
        total_stacks=len(applicable),
        drifted_stacks=len(drifted),
        violations=violations,
        exempt_stacks=list(exempt),
    )


def render_compliance_text(result: ComplianceResult) -> str:
    """Render a human-readable compliance report."""
    lines = [
        f"Compliance Report",
        f"  Total stacks : {result.total_stacks}",
        f"  Drifted      : {result.drifted_stacks} ({result.drifted_pct:.1f}%)",
        f"  Exempt       : {len(result.exempt_stacks)}",
        f"  Status       : {'COMPLIANT' if result.is_compliant else 'NON-COMPLIANT'}",
    ]
    if result.violations:
        lines.append("  Violations:")
        for v in result.violations:
            lines.append(f"    - {v.stack_name}: {v.reason}")
    return "\n".join(lines)
