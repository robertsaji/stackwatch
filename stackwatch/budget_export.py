"""Export budget check results to JSON or plain-text files."""
from __future__ import annotations

import json
from pathlib import Path

from stackwatch.budget import BudgetResult, render_budget_text


class BudgetExportError(Exception):
    """Raised when a budget export operation fails."""


def _ensure_dir(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BudgetExportError(f"Cannot create directory {path.parent}: {exc}") from exc


def _result_to_dict(result: BudgetResult) -> dict:
    return {
        "drifted_resource_count": result.drifted_resource_count,
        "estimated_cost": result.estimated_cost,
        "monthly_budget": result.monthly_budget,
        "warn_threshold": result.warn_threshold,
        "budget_remaining": result.budget_remaining,
        "budget_used_fraction": result.budget_used_fraction,
        "over_budget": result.over_budget,
        "near_budget": result.near_budget,
    }


def export_budget_json(result: BudgetResult, path: Path) -> None:
    """Write *result* as JSON to *path*, creating parent directories as needed."""
    _ensure_dir(path)
    try:
        path.write_text(json.dumps(_result_to_dict(result), indent=2))
    except OSError as exc:
        raise BudgetExportError(f"Failed to write {path}: {exc}") from exc


def export_budget_text(result: BudgetResult, path: Path) -> None:
    """Write a human-readable budget summary to *path*."""
    _ensure_dir(path)
    try:
        path.write_text(render_budget_text(result))
    except OSError as exc:
        raise BudgetExportError(f"Failed to write {path}: {exc}") from exc
