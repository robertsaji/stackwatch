"""HTML and plain-text report generation for drift results."""
from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from stackwatch.drift import DriftResult


@dataclass
class Report:
    generated_at: str
    total_stacks: int
    drifted_stacks: int
    results: List[DriftResult]

    @property
    def has_drift(self) -> bool:
        return self.drifted_stacks > 0


def build_report(results: List[DriftResult]) -> Report:
    """Build a Report from a list of DriftResult objects."""
    drifted = sum(1 for r in results if r.drifted)
    return Report(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_stacks=len(results),
        drifted_stacks=drifted,
        results=results,
    )


def render_text(report: Report) -> str:
    """Render a plain-text summary of the report."""
    lines = [
        f"StackWatch Drift Report — {report.generated_at}",
        f"Stacks checked : {report.total_stacks}",
        f"Drifted stacks : {report.drifted_stacks}",
        "-" * 48,
    ]
    for result in report.results:
        status = "DRIFTED" if result.drifted else "IN_SYNC"
        lines.append(f"  [{status}] {result.stack_name}")
        for resource in result.drifted_resources:
            lines.append(
                f"    • {resource.logical_id} ({resource.resource_type}): "
                f"{resource.drift_status}"
            )
    return "\n".join(lines)


def render_html(report: Report) -> str:
    """Render a minimal HTML summary of the report."""
    rows = ""
    for result in report.results:
        status = "DRIFTED" if result.drifted else "IN_SYNC"
        color = "#c0392b" if result.drifted else "#27ae60"
        rows += (
            f'<tr><td>{result.stack_name}</td>'
            f'<td style="color:{color};font-weight:bold">{status}</td>'
            f"<td>{len(result.drifted_resources)}</td></tr>\n"
        )
    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><title>StackWatch Report</title></head>
        <body>
        <h2>StackWatch Drift Report</h2>
        <p>Generated: {report.generated_at}</p>
        <p>Stacks checked: {report.total_stacks} &nbsp;|&nbsp;
           Drifted: {report.drifted_stacks}</p>
        <table border="1" cellpadding="4" cellspacing="0">
        <thead><tr><th>Stack</th><th>Status</th><th>Drifted Resources</th></tr></thead>
        <tbody>
        {rows}</tbody>
        </table>
        </body></html>
    """)
