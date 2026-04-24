"""Export grouping reports to JSON or text files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from stackwatch.grouping import GroupingReport, render_grouping_text


class GroupingExportError(Exception):
    """Raised when a grouping export operation fails."""


def _ensure_dir(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GroupingExportError(f"Cannot create directory {path.parent}: {exc}") from exc


def _report_to_dict(report: GroupingReport) -> List[dict]:
    return [
        {
            "group": g.name,
            "total": g.total,
            "drifted": g.drifted,
            "drift_rate": round(g.drift_rate, 4),
        }
        for g in sorted(report.groups, key=lambda g: g.name)
    ]


def export_grouping_json(report: GroupingReport, path: Path) -> None:
    """Write the grouping report as JSON to *path*."""
    _ensure_dir(path)
    try:
        data = _report_to_dict(report)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        raise GroupingExportError(f"Failed to write JSON to {path}: {exc}") from exc


def export_grouping_text(report: GroupingReport, path: Path) -> None:
    """Write the grouping report as plain text to *path*."""
    _ensure_dir(path)
    try:
        path.write_text(render_grouping_text(report), encoding="utf-8")
    except OSError as exc:
        raise GroupingExportError(f"Failed to write text to {path}: {exc}") from exc
