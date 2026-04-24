"""CLI commands for stack grouping."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from stackwatch.grouping import (
    GroupingConfig,
    build_grouping_report,
    render_grouping_text,
)
from stackwatch.snapshot import Snapshot


def _load_snapshot(path: str) -> Snapshot:
    snap = Snapshot.load(Path(path))
    if snap is None:
        raise click.ClickException(f"Snapshot not found: {path}")
    return snap


@click.group(name="grouping")
def grouping_group() -> None:
    """Commands for grouping stacks by tag or prefix."""


@grouping_group.command(name="show")
@click.argument("snapshot_path")
@click.option("--tag-key", default=None, help="AWS tag key to group by.")
@click.option(
    "--prefix-delimiter",
    default=None,
    help="Delimiter for name-prefix grouping (e.g. '-').",
)
@click.option(
    "--fallback", default="ungrouped", show_default=True, help="Fallback group name."
)
def show_command(
    snapshot_path: str,
    tag_key: Optional[str],
    prefix_delimiter: Optional[str],
    fallback: str,
) -> None:
    """Show drift grouped by tag or prefix from a snapshot."""
    try:
        config = GroupingConfig(
            tag_key=tag_key,
            prefix_delimiter=prefix_delimiter,
            fallback_group=fallback,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    snap = _load_snapshot(snapshot_path)
    report = build_grouping_report(snap.results, config)
    click.echo(render_grouping_text(report))


@grouping_group.command(name="json")
@click.argument("snapshot_path")
@click.option("--tag-key", default=None)
@click.option("--prefix-delimiter", default=None)
@click.option("--fallback", default="ungrouped")
def json_command(
    snapshot_path: str,
    tag_key: Optional[str],
    prefix_delimiter: Optional[str],
    fallback: str,
) -> None:
    """Output grouping report as JSON."""
    try:
        config = GroupingConfig(
            tag_key=tag_key,
            prefix_delimiter=prefix_delimiter,
            fallback_group=fallback,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    snap = _load_snapshot(snapshot_path)
    report = build_grouping_report(snap.results, config)
    data = [
        {
            "group": g.name,
            "total": g.total,
            "drifted": g.drifted,
            "drift_rate": round(g.drift_rate, 4),
        }
        for g in sorted(report.groups, key=lambda g: g.name)
    ]
    click.echo(json.dumps(data, indent=2))
