"""Export a CompareReport to JSON or text files."""
from __future__ import annotations
import json
from pathlib import Path
from stackwatch.compare import CompareReport, render_compare_text


class CompareExportError(Exception):
    pass


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def export_compare_json(report: CompareReport, dest: Path) -> None:
    _ensure_dir(dest)
    data = {
        "newly_drifted": report.newly_drifted,
        "resolved": report.resolved,
        "still_drifted": report.still_drifted,
        "unchanged_clean": report.unchanged_clean,
        "has_changes": report.has_changes,
    }
    try:
        dest.write_text(json.dumps(data, indent=2))
    except OSError as exc:
        raise CompareExportError(f"Failed to write {dest}: {exc}") from exc


def export_compare_text(report: CompareReport, dest: Path) -> None:
    _ensure_dir(dest)
    try:
        dest.write_text(render_compare_text(report))
    except OSError as exc:
        raise CompareExportError(f"Failed to write {dest}: {exc}") from exc
