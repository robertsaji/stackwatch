"""CLI commands for drift risk scoring."""
from __future__ import annotations

import click

from stackwatch.config import load_config
from stackwatch.drift import DriftDetector
from stackwatch.scoring import build_scoring_report, render_scoring_text


@click.group(name="scoring")
def scoring_group() -> None:
    """Drift risk scoring commands."""


@scoring_group.command(name="check")
@click.option("--config", "cfg_path", default=None, help="Path to config file.")
@click.option(
    "--min-score",
    default=0,
    show_default=True,
    help="Only show stacks with score >= this value.",
)
@click.option(
    "--exit-nonzero",
    is_flag=True,
    default=False,
    help="Exit with code 1 if any CRITICAL stack is found.",
)
def check_command(cfg_path: str | None, min_score: int, exit_nonzero: bool) -> None:
    """Detect drift and display risk scores for all monitored stacks."""
    cfg = load_config(cfg_path)
    detector = DriftDetector(cfg.aws)
    results = detector.detect_all()
    report = build_scoring_report(results)

    filtered = [
        s for s in report.scores if s.score >= min_score
    ]

    if not filtered:
        click.echo("No stacks meet the minimum score threshold.")
        return

    from stackwatch.scoring import ScoringReport, render_scoring_text as _render
    display = ScoringReport(scores=filtered)
    click.echo(_render(display))

    if exit_nonzero and any(s.label == "CRITICAL" for s in filtered):
        raise SystemExit(1)
