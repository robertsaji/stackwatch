"""CLI commands for the drift archiver."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.archiver import ArchiveError, DriftArchiver
from stackwatch.snapshot import Snapshot, SnapshotError

_DEFAULT_ARCHIVE_DIR = Path(".stackwatch/archive")
_DEFAULT_SNAP = Path(".stackwatch/snapshot.json")


def _get_archiver(archive_dir: str) -> DriftArchiver:
    return DriftArchiver(archive_dir=Path(archive_dir))


@click.group(name="archive")
def archive_group() -> None:
    """Manage compressed drift snapshot archives."""


@archive_group.command(name="save")
@click.option("--snapshot", "snap_path", default=str(_DEFAULT_SNAP), show_default=True)
@click.option("--dir", "archive_dir", default=str(_DEFAULT_ARCHIVE_DIR), show_default=True)
def save_command(snap_path: str, archive_dir: str) -> None:
    """Compress the current snapshot and add it to the archive."""
    try:
        snap = Snapshot.load(Path(snap_path))
    except SnapshotError as exc:
        raise click.ClickException(str(exc))
    if snap is None:
        raise click.ClickException(f"No snapshot found at {snap_path}")
    try:
        archiver = _get_archiver(archive_dir)
        entry = archiver.archive(snap)
        click.echo(f"Archived {entry.stack_count} stacks ({entry.drifted_count} drifted) -> {entry.filename}")
    except ArchiveError as exc:
        raise click.ClickException(str(exc))


@archive_group.command(name="list")
@click.option("--dir", "archive_dir", default=str(_DEFAULT_ARCHIVE_DIR), show_default=True)
def list_command(archive_dir: str) -> None:
    """List all archived snapshots."""
    try:
        archiver = _get_archiver(archive_dir)
        entries = archiver.list_entries()
    except ArchiveError as exc:
        raise click.ClickException(str(exc))
    if not entries:
        click.echo("No archives found.")
        return
    click.echo(f"{'Timestamp':<20} {'Stacks':>8} {'Drifted':>8}  File")
    click.echo("-" * 60)
    for e in entries:
        click.echo(f"{e.timestamp:<20} {e.stack_count:>8} {e.drifted_count:>8}  {e.filename}")


@archive_group.command(name="load")
@click.argument("filename")
@click.option("--dir", "archive_dir", default=str(_DEFAULT_ARCHIVE_DIR), show_default=True)
def load_command(filename: str, archive_dir: str) -> None:
    """Decompress and display a summary of an archived snapshot."""
    try:
        archiver = _get_archiver(archive_dir)
        snap = archiver.load(filename)
    except ArchiveError as exc:
        raise click.ClickException(str(exc))
    drifted = snap.drifted()
    click.echo(f"Stacks: {len(snap.stack_names())}  Drifted: {len(drifted)}")
    for r in drifted:
        click.echo(f"  [DRIFTED] {r.stack_name}")
