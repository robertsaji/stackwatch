"""CLI commands for stale drift detection."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from stackwatch.config import load_config
from stackwatch.drift import DriftDetector
from stackwatch.history import DriftHistory
from stackwatch.stale import StaleConfig, StaleError, build_stale_report, render_stale_text


def _get_history(path: str) -> DriftHistory:
    return DriftHistory(Path(path))


@click.group(name="stale")
def stale_group() -> None:
    """Commands for identifying stacks with overdue drift checks."""


@stale_group.command(name="check")
@click.option("--max-age-hours", default=24.0, show_default=True, help="Hours before a stack is considered stale.")
@click.option("--history-file", default=".stackwatch/history.json", show_default=True)
@click.option("--exit-code", is_flag=True, default=False, help="Exit non-zero if any stacks are stale.")
def check_command(max_age_hours: float, history_file: str, exit_code: bool) -> None:
    """Check which stacks have not been inspected recently."""
    try:
        cfg = StaleConfig(max_age_hours=max_age_hours)
    except StaleError as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(2)

    app_config = load_config()
    detector = DriftDetector(app_config.aws)
    results = detector.detect_all()

    history = _get_history(history_file)
    entries = history.load()

    report = build_stale_report(results, entries, cfg)
    click.echo(render_stale_text(report))

    if exit_code and report.stale_count > 0:
        sys.exit(1)


@stale_group.command(name="list")
@click.option("--max-age-hours", default=24.0, show_default=True)
@click.option("--history-file", default=".stackwatch/history.json", show_default=True)
def list_command(max_age_hours: float, history_file: str) -> None:
    """List only the stale stacks."""
    try:
        cfg = StaleConfig(max_age_hours=max_age_hours)
    except StaleError as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(2)

    app_config = load_config()
    detector = DriftDetector(app_config.aws)
    results = detector.detect_all()

    history = _get_history(history_file)
    entries = history.load()

    report = build_stale_report(results, entries, cfg)
    if not report.stale:
        click.echo("No stale stacks found.")
        return
    for sr in report.stale:
        age_str = f"{sr.age_hours:.1f}h" if sr.age_hours is not None else "never"
        click.echo(f"{sr.stack_name}\t{age_str}")
