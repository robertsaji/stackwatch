"""Export scoring reports to JSON or text files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from stackwatch.scoring import ScoringReport, StackScore, render_scoring_text


class ScoringExportError(Exception):
    """Raised when a scoring export operation fails."""


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _score_to_dict(score: StackScore) -> dict:
    return {
        "stack_name": score.stack_name,
        "score": score.score,
        "drifted_count": score.drifted_count,
        "total_resources": score.total_resources,
        "label": score.label,
    }


def export_scoring_json(report: ScoringReport, path: str | Path) -> None:
    """Write a ScoringReport to a JSON file."""
    dest = Path(path)
    _ensure_dir(dest)
    payload = {
        "average_score": round(report.average_score, 2),
        "stacks": [_score_to_dict(s) for s in report.scores],
    }
    try:
        dest.write_text(json.dumps(payload, indent=2))
    except OSError as exc:
        raise ScoringExportError(f"Failed to write JSON to {dest}: {exc}") from exc


def export_scoring_text(report: ScoringReport, path: str | Path) -> None:
    """Write a human-readable scoring report to a text file."""
    dest = Path(path)
    _ensure_dir(dest)
    try:
        dest.write_text(render_scoring_text(report))
    except OSError as exc:
        raise ScoringExportError(f"Failed to write text to {dest}: {exc}") from exc


def load_scoring_json(path: str | Path) -> ScoringReport:
    """Load a previously exported ScoringReport from JSON."""
    src = Path(path)
    if not src.exists():
        raise ScoringExportError(f"File not found: {src}")
    try:
        data = json.loads(src.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ScoringExportError(f"Failed to read {src}: {exc}") from exc
    scores: List[StackScore] = [
        StackScore(
            stack_name=s["stack_name"],
            score=s["score"],
            drifted_count=s["drifted_count"],
            total_resources=s["total_resources"],
            label=s["label"],
        )
        for s in data.get("stacks", [])
    ]
    return ScoringReport(scores=scores)
