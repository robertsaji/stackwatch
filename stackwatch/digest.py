"""Periodic digest builder: aggregates multiple DriftResults into a summary digest."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from stackwatch.drift import DriftResult


@dataclass
class DigestEntry:
    stack_name: str
    status: str
    drifted_count: int


@dataclass
class Digest:
    created_at: datetime
    entries: List[DigestEntry] = field(default_factory=list)

    @property
    def total_stacks(self) -> int:
        return len(self.entries)

    @property
    def drifted_stacks(self) -> int:
        return sum(1 for e in self.entries if e.status == "DRIFTED")


def build_digest(results: list[DriftResult]) -> Digest:
    entries = [
        DigestEntry(
            stack_name=r.stack_name,
            status=r.status,
            drifted_count=len(r.drifted_resources),
        )
        for r in results
    ]
    return Digest(created_at=datetime.now(timezone.utc), entries=entries)


def render_digest_text(digest: Digest) -> str:
    lines = [
        f"StackWatch Digest — {digest.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Stacks checked : {digest.total_stacks}",
        f"Drifted stacks : {digest.drifted_stacks}",
        "",
    ]
    for entry in digest.entries:
        indicator = "[DRIFT]" if entry.status == "DRIFTED" else "[OK]   "
        lines.append(f"  {indicator} {entry.stack_name} ({entry.drifted_count} resources drifted)")
    return "\n".join(lines)


def render_digest_html(digest: Digest) -> str:
    rows = "".join(
        f"<tr><td>{e.stack_name}</td><td>{e.status}</td><td>{e.drifted_count}</td></tr>"
        for e in digest.entries
    )
    return (
        f"<h2>StackWatch Digest</h2>"
        f"<p>Checked: {digest.total_stacks} | Drifted: {digest.drifted_stacks}</p>"
        f"<table><tr><th>Stack</th><th>Status</th><th>Drifted Resources</th></tr>{rows}</table>"
    )
