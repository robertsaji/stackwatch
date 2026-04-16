"""Remediation hints for drifted CloudFormation stacks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from stackwatch.drift import DriftResult, DriftedResource


@dataclass
class RemediationHint:
    resource_id: str
    resource_type: str
    action: str
    detail: str


@dataclass
class RemediationReport:
    stack_name: str
    hints: List[RemediationHint]

    @property
    def has_hints(self) -> bool:
        return bool(self.hints)


_ACTION_MAP = {
    "MODIFIED": "update",
    "DELETED": "recreate",
    "NOT_CHECKED": "inspect",
}


def _hint_for_resource(resource: DriftedResource) -> RemediationHint:
    action = _ACTION_MAP.get(resource.drift_status, "review")
    detail = (
        f"Resource '{resource.resource_id}' of type '{resource.resource_type}' "
        f"has drift status '{resource.drift_status}'. "
        f"Recommended action: {action} via CloudFormation stack update or import."
    )
    return RemediationHint(
        resource_id=resource.resource_id,
        resource_type=resource.resource_type,
        action=action,
        detail=detail,
    )


def build_remediation_report(result: DriftResult) -> RemediationReport:
    hints = [_hint_for_resource(r) for r in result.drifted_resources]
    return RemediationReport(stack_name=result.stack_name, hints=hints)


def render_remediation_text(report: RemediationReport) -> str:
    if not report.has_hints:
        return f"Stack '{report.stack_name}': no remediation needed."
    lines = [f"Remediation hints for stack '{report.stack_name}':"]
    for hint in report.hints:
        lines.append(f"  [{hint.action.upper()}] {hint.resource_id} ({hint.resource_type})")
        lines.append(f"    {hint.detail}")
    return "\n".join(lines)
