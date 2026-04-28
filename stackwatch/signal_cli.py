"""CLI commands for the signal aggregation feature."""
from __future__ import annotations

import json
from pathlib import Path

import click

from stackwatch.signal import SignalConfig, build_signal_report, render_signal_text
from stackwatch.snapshot import Snapshot


def _load_snapshot(path: str) -> Snapshot:
    snap = Snapshot.load(Path(path))
    if snap is None:
        raise click.ClickException(f"Snapshot not found: {path}")
    return snap


@click.group("signal")
def signal_group() -> None:
    """Aggregate drift signals across stacks."""


@signal_group.command("show")
@click.argument("snapshot_path")
@click.option("--top", default=10, show_default=True, help="Number of top stacks to show.")
@click.option("--min-score", default=0.0, show_default=True, help="Minimum score to display.")
def show_command(snapshot_path: str, top: int, min_score: float) -> None:
    """Show signal scores for stacks in a snapshot."""
    snap = _load_snapshot(snapshot_path)
    report = build_signal_report(list(snap.results.values()))
    filtered = [s for s in report.top(top) if s.score >= min_score]
    if not filtered:
        click.echo("No signals above threshold.")
        return
    for sig in filtered:
        click.echo(f"[{sig.label.upper():8s}] {sig.stack_name}  score={sig.score}")


@signal_group.command("text")
@click.argument("snapshot_path")
def text_command(snapshot_path: str) -> None:
    """Render full signal report as text."""
    snap = _load_snapshot(snapshot_path)
    report = build_signal_report(list(snap.results.values()))
    click.echo(render_signal_text(report))


@signal_group.command("json")
@click.argument("snapshot_path")
def json_command(snapshot_path: str) -> None:
    """Render signal report as JSON."""
    snap = _load_snapshot(snapshot_path)
    report = build_signal_report(list(snap.results.values()))
    data = [
        {
            "stack_name": s.stack_name,
            "score": s.score,
            "label": s.label,
            "drifted_count": s.drifted_count,
            "total_count": s.total_count,
        }
        for s in report.signals
    ]
    click.echo(json.dumps(data, indent=2))
