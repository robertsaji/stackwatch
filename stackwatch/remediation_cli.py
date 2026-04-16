"""CLI commands for remediation hints."""
from __future__ import annotations

import click

from stackwatch.config import load_config
from stackwatch.drift import DriftDetector
from stackwatch.remediation import build_remediation_report, render_remediation_text


@click.group(name="remediation")
def remediation_group() -> None:
    """Remediation hint commands."""


@remediation_group.command(name="show")
@click.argument("stack_name")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def show_hints(stack_name: str, config_path: str | None) -> None:
    """Show remediation hints for a drifted stack."""
    cfg = load_config(config_path)
    detector = DriftDetector(cfg.aws)
    result = detector.detect(stack_name)
    report = build_remediation_report(result)
    click.echo(render_remediation_text(report))


@remediation_group.command(name="show-all")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def show_all_hints(config_path: str | None) -> None:
    """Show remediation hints for all monitored stacks."""
    cfg = load_config(config_path)
    detector = DriftDetector(cfg.aws)
    results = detector.detect_all()
    for result in results:
        report = build_remediation_report(result)
        if report.has_hints:
            click.echo(render_remediation_text(report))
            click.echo()
