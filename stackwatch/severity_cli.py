"""CLI commands for drift severity reporting."""
from __future__ import annotations
import click
from stackwatch.severity import SeverityLevel, classify_all, render_severity_text


@click.group(name="severity")
def severity_group() -> None:
    """Drift severity commands."""


@severity_group.command(name="check")
@click.option("--stack", multiple=True, help="Stack names to check (all if omitted).")
@click.option("--min-level", type=click.Choice([l.value for l in SeverityLevel]), default="low", show_default=True)
@click.pass_context
def check_command(ctx: click.Context, stack: tuple, min_level: str) -> None:
    """Detect and display drift severity for stacks."""
    from stackwatch.config import load_config
    from stackwatch.drift import DriftDetector

    cfg = load_config()
    detector = DriftDetector(cfg.aws)
    stacks = list(stack) or None
    results = detector.detect_all(stacks)
    severity_results = classify_all(results)

    threshold = SeverityLevel(min_level)
    order = list(SeverityLevel)
    filtered = [r for r in severity_results if order.index(r.level) >= order.index(threshold)]

    click.echo(render_severity_text(filtered))
    if any(r.level in (SeverityLevel.HIGH, SeverityLevel.CRITICAL) for r in filtered):
        raise SystemExit(1)
