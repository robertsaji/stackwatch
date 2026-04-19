"""Enrich drift results with runbook links."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from stackwatch.drift import DriftResult
from stackwatch.runbook import RunbookStore


@dataclass
class EnrichedResult:
    result: DriftResult
    runbook_url: Optional[str]

    @property
    def stack_name(self) -> str:
        return self.result.stack_name

    @property
    def has_runbook(self) -> bool:
        return self.runbook_url is not None


def enrich(results: List[DriftResult], store: RunbookStore) -> List[EnrichedResult]:
    """Attach runbook URLs to each drift result."""
    return [
        EnrichedResult(result=r, runbook_url=store.get(r.stack_name))
        for r in results
    ]


def render_enriched_text(enriched: List[EnrichedResult]) -> str:
    """Render a plain-text summary including runbook links where available."""
    lines: List[str] = []
    for entry in enriched:
        status = "DRIFTED" if entry.result.has_drift else "IN_SYNC"
        line = f"[{status}] {entry.stack_name}"
        if entry.has_runbook:
            line += f"  -> runbook: {entry.runbook_url}"
        lines.append(line)
    return "\n".join(lines)
