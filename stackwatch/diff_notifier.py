"""Notifier that alerts only when drift state changes between snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from stackwatch.snapshot import Snapshot
from stackwatch.snapshot_reporter import build_diff_report, render_diff_text, SnapshotDiffReport
from stackwatch.notifier import Notifier
from stackwatch.drift import DriftResult


class DiffNotifierError(Exception):
    pass


@dataclass
class DiffNotifier:
    """Wraps a Notifier and only fires when drift changes vs a previous snapshot."""

    notifier: Notifier
    previous: Optional[Snapshot] = None

    def notify_changes(self, results: list[DriftResult], current: Snapshot) -> SnapshotDiffReport:
        """Send notifications for stacks whose drift state changed.

        Returns the diff report regardless of whether anything was sent.
        """
        report = build_diff_report(self.previous, current)

        if self.previous is None:
            # First run — notify all drifted stacks
            changed_names = {r.stack_name for r in results if r.has_drift}
        else:
            changed_names = (
                set(report.newly_drifted) | set(report.newly_resolved)
            )

        for result in results:
            if result.stack_name in changed_names:
                self.notifier.send(result)

        return report

    def render(self, report: SnapshotDiffReport) -> str:
        return render_diff_text(report)
