"""CLI commands for comparing two named snapshots."""
import click
from pathlib import Path
from stackwatch.snapshot import Snapshot
from stackwatch.compare import compare_snapshots, render_compare_text


def _load(path: str) -> Snapshot:
    p = Path(path)
    snap = Snapshot.load(p)
    if snap is None:
        raise click.ClickException(f"Snapshot not found: {path}")
    return snap


@click.group("compare")
def compare_group() -> None:
    """Compare two drift snapshots."""


@compare_group.command("diff")
@click.argument("before")
@click.argument("after")
def diff_command(before: str, after: str) -> None:
    """Show drift changes between BEFORE and AFTER snapshot files."""
    snap_before = _load(before)
    snap_after = _load(after)
    report = compare_snapshots(snap_before, snap_after)
    click.echo(render_compare_text(report))
    if report.newly_drifted:
        raise SystemExit(1)


@compare_group.command("summary")
@click.argument("before")
@click.argument("after")
def summary_command(before: str, after: str) -> None:
    """Print a one-line summary of changes between snapshots."""
    snap_before = _load(before)
    snap_after = _load(after)
    report = compare_snapshots(snap_before, snap_after)
    click.echo(
        f"newly_drifted={len(report.newly_drifted)} "
        f"resolved={len(report.resolved)} "
        f"still_drifted={len(report.still_drifted)}"
    )
