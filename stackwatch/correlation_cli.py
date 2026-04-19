"""CLI commands for drift correlation."""
from __future__ import annotations
import click
from stackwatch.correlation import build_correlation_report, render_correlation_text
from stackwatch.snapshot import Snapshot


def _load(path: str) -> Snapshot:
    snap = Snapshot.load(path)
    if snap is None:
        raise click.ClickException(f"Snapshot not found: {path}")
    return snap


@click.group(name="correlation")
def correlation_group() -> None:
    """Drift correlation commands."""


@correlation_group.command(name="show")
@click.argument("snapshot_path")
@click.option("--min-count", default=2, show_default=True, help="Minimum stack count to display.")
def show_command(snapshot_path: str, min_count: int) -> None:
    """Show correlated drift resource types from a snapshot."""
    snap = _load(snapshot_path)
    report = build_correlation_report(snap.results)
    filtered = [g for g in report.groups if g.count >= min_count]
    report.groups = filtered
    click.echo(render_correlation_text(report))
    if report.has_correlations:
        raise SystemExit(1)
