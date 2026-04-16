"""Generate summary reports from the audit log."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from stackwatch.audit import AuditEntry, AuditLog


@dataclass
class AuditReport:
    total_events: int
    drifted_events: int
    stacks_seen: int
    top_drifters: List[tuple]  # (stack_name, drift_event_count)


def build_audit_report(log: AuditLog) -> AuditReport:
    entries = log.entries()
    drift_counts: Dict[str, int] = {}
    drifted_events = 0
    stacks: set = set()

    for e in entries:
        stacks.add(e.stack_name)
        if e.status == "DRIFTED":
            drifted_events += 1
            drift_counts[e.stack_name] = drift_counts.get(e.stack_name, 0) + 1

    top_drifters = sorted(drift_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return AuditReport(
        total_events=len(entries),
        drifted_events=drifted_events,
        stacks_seen=len(stacks),
        top_drifters=top_drifters,
    )


def render_audit_report_text(report: AuditReport) -> str:
    lines = [
        "=== Audit Report ===",
        f"Total events  : {report.total_events}",
        f"Drifted events: {report.drifted_events}",
        f"Stacks seen   : {report.stacks_seen}",
    ]
    if report.top_drifters:
        lines.append("Top drifters:")
        for name, count in report.top_drifters:
            lines.append(f"  {name}: {count} drift event(s)")
    return "\n".join(lines)
