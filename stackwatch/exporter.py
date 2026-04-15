"""Export drift reports to files (JSON, text, HTML)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from stackwatch.reporter import Report, render_html, render_text


class ExportError(Exception):
    """Raised when a report cannot be written to disk."""


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def export_text(report: Report, dest: str) -> Path:
    """Write a plain-text report and return the resolved path."""
    out = Path(dest).resolve()
    _ensure_dir(out)
    try:
        out.write_text(render_text(report), encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Failed to write text report to {out}: {exc}") from exc
    return out


def export_html(report: Report, dest: str) -> Path:
    """Write an HTML report and return the resolved path."""
    out = Path(dest).resolve()
    _ensure_dir(out)
    try:
        out.write_text(render_html(report), encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Failed to write HTML report to {out}: {exc}") from exc
    return out


def export_json(report: Report, dest: str) -> Path:
    """Write a JSON report and return the resolved path."""
    out = Path(dest).resolve()
    _ensure_dir(out)
    payload = {
        "generated_at": report.generated_at,
        "total_stacks": report.total_stacks,
        "drifted_stacks": report.drifted_stacks,
        "results": [
            {
                "stack_name": r.stack_name,
                "drifted": r.drifted,
                "drifted_resources": [
                    {
                        "logical_id": res.logical_id,
                        "resource_type": res.resource_type,
                        "drift_status": res.drift_status,
                    }
                    for res in r.drifted_resources
                ],
            }
            for r in report.results
        ],
    }
    try:
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Failed to write JSON report to {out}: {exc}") from exc
    return out
