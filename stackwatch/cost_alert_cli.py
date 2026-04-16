"""CLI commands for cost-aware alert filtering."""
from __future__ import annotations

import click

from stackwatch.config import load_config
from stackwatch.cost_alert import CostAlertConfig, CostAlertFilter
from stackwatch.drift import DriftDetector


@click.group(name="cost-alert")
def cost_alert_group() -> None:
    """Cost-aware drift alert commands."""


@cost_alert_group.command("check")
@click.option("--min-cost", default=0.0, show_default=True, help="Minimum monthly cost (USD) to alert.")
@click.option("--stack", multiple=True, help="Stack names to check (repeatable).")
@click.option("--config", "config_path", default=None, help="Path to stackwatch config file.")
def check_command(min_cost: float, stack: tuple, config_path: str | None) -> None:
    """Detect drift and show which stacks would trigger cost-filtered alerts."""
    app_cfg = load_config(config_path)
    session_kwargs = {
        "region_name": app_cfg.aws.region,
    }
    if app_cfg.aws.profile:
        session_kwargs["profile_name"] = app_cfg.aws.profile

    import boto3
    session = boto3.Session(**session_kwargs)
    detector = DriftDetector(session)

    stack_names = list(stack) if stack else None
    results = detector.detect_all(stack_names)

    cost_cfg = CostAlertConfig(min_monthly_cost=min_cost)
    filt = CostAlertFilter(cost_cfg)
    evaluated = filt.apply(results)

    alerted = [e for e in evaluated if not e.suppressed]
    suppressed = [e for e in evaluated if e.suppressed]

    if alerted:
        click.echo(click.style(f"Alerting on {len(alerted)} stack(s):", fg="red"))
        for e in alerted:
            cost_str = f"${e.cost:.2f}/mo" if e.cost is not None else "cost unknown"
            click.echo(f"  {e.result.stack_name}  [{cost_str}]")
    else:
        click.echo(click.style("No stacks require alerting.", fg="green"))

    if suppressed:
        click.echo(f"Suppressed {len(suppressed)} stack(s) (no drift or below cost threshold).")
