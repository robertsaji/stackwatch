"""Generate a simple HTML status page summarising current drift state."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from stackwatch.drift import DriftResult


@dataclass
class StatusPage:
    generated_at: datetime
    total_stacks: int
    drifted_stacks: int
    in_sync_stacks: int
    results: List[DriftResult]

    @property
    def drift_rate(self) -> float:
        if self.total_stacks == 0:
            return 0.0
        return self.drifted_stacks / self.total_stacks


def build_status_page(results: List[DriftResult]) -> StatusPage:
    drifted = [r for r in results if r.has_drift]
    return StatusPage(
        generated_at=datetime.now(timezone.utc),
        total_stacks=len(results),
        drifted_stacks=len(drifted),
        in_sync_stacks=len(results) - len(drifted),
        results=results,
    )


def render_status_html(page: StatusPage) -> str:
    rows = []
    for r in page.results:
        status = "DRIFTED" if r.has_drift else "IN_SYNC"
        colour = "#c0392b" if r.has_drift else "#27ae60"
        resource_count = len(r.drifted_resources)
        rows.append(
            f"<tr><td>{r.stack_name}</td>"
            f"<td style='color:{colour}'>{status}</td>"
            f"<td>{resource_count}</td></tr>"
        )
    rows_html = "\n".join(rows)
    ts = page.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    rate_pct = f"{page.drift_rate * 100:.1f}"
    return f"""<!DOCTYPE html>
<html>
<head><title>StackWatch Status</title></head>
<body>
<h1>StackWatch Drift Status</h1>
<p>Generated: {ts}</p>
<p>Total: {page.total_stacks} | Drifted: {page.drifted_stacks} | In Sync: {page.in_sync_stacks} | Drift Rate: {rate_pct}%</p>
<table border="1" cellpadding="4">
<tr><th>Stack</th><th>Status</th><th>Drifted Resources</th></tr>
{rows_html}
</table>
</body>
</html>"""


def render_status_text(page: StatusPage) -> str:
    lines = [
        f"StackWatch Status — {page.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Total: {page.total_stacks}  Drifted: {page.drifted_stacks}  "
        f"In Sync: {page.in_sync_stacks}  Rate: {page.drift_rate * 100:.1f}%",
        "-" * 50,
    ]
    for r in page.results:
        status = "DRIFTED" if r.has_drift else "IN_SYNC"
        lines.append(f"  {r.stack_name:<40} {status}")
    return "\n".join(lines)
