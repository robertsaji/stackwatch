"""CLI commands for budget-aware drift cost estimation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from stackwatch.budget import BudgetConfig, BudgetError, check_budget, render_budget_text
from stackwatch.snapshot import Snapshot


@click.group(name="budget")
def budget_group() -> None:
    """Budget-aware drift cost commands."""


@budget_group.command(name="check")
@click.argument("snapshot_file", type=click.Path(exists=True))
@click.option("--cost-per-resource", default=5.0, show_default=True,
              help="Estimated USD cost per drifted resource.")
@click.option("--monthly-budget", default=500.0, show_default=True,
              help="Monthly remediation budget in USD.")
@click.option("--warn-threshold", default=0.80, show_default=True,
              help="Fraction of budget that triggers a warning (0–1).")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output result as JSON.")
def check_command(
    snapshot_file: str,
    cost_per_resource: float,
    monthly_budget: float,
    warn_threshold: float,
    as_json: bool,
) -> None:
    """Estimate remediation cost from a saved snapshot and compare to budget."""
    try:
        cfg = BudgetConfig(
            cost_per_drifted_resource=cost_per_resource,
            monthly_budget=monthly_budget,
            warn_threshold=warn_threshold,
        )
    except BudgetError as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(2)

    snap = Snapshot.load(Path(snapshot_file))
    if snap is None:
        click.echo("Snapshot file is empty or invalid.", err=True)
        sys.exit(2)

    result = check_budget(list(snap.results.values()), cfg)

    if as_json:
        click.echo(json.dumps({
            "drifted_resource_count": result.drifted_resource_count,
            "estimated_cost": result.estimated_cost,
            "monthly_budget": result.monthly_budget,
            "budget_remaining": result.budget_remaining,
            "budget_used_fraction": result.budget_used_fraction,
            "over_budget": result.over_budget,
            "near_budget": result.near_budget,
        }, indent=2))
    else:
        click.echo(render_budget_text(result))

    if result.over_budget:
        sys.exit(1)
