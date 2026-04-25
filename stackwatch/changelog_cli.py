"""CLI commands for the drift changelog."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.changelog import Changelog, render_changelog_text


DEFAULT_PATH = Path(".stackwatch/changelog.json")


def _get_changelog(path: str) -> Changelog:
    return Changelog(path=Path(path))


@click.group(name="changelog")
def changelog_group() -> None:
    """Manage the drift state changelog."""


@changelog_group.command(name="list")
@click.option("--file", "store_file", default=str(DEFAULT_PATH), show_default=True)
@click.option("--stack", default=None, help="Filter by stack name.")
def list_entries(store_file: str, stack: str | None) -> None:
    """List changelog entries."""
    log = _get_changelog(store_file)
    entries = log.entries_for(stack) if stack else log.all_entries()
    if not entries:
        click.echo("No changelog entries.")
        return
    for e in entries:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        click.echo(f"[{ts}] {e.stack_name}: {e.previous_state} -> {e.current_state} ({e.drifted_count} drifted)")


@changelog_group.command(name="show")
@click.option("--file", "store_file", default=str(DEFAULT_PATH), show_default=True)
def show_command(store_file: str) -> None:
    """Render full changelog as text."""
    log = _get_changelog(store_file)
    click.echo(render_changelog_text(log))


@changelog_group.command(name="clear")
@click.option("--file", "store_file", default=str(DEFAULT_PATH), show_default=True)
@click.confirmation_option(prompt="Clear all changelog entries?")
def clear_entries(store_file: str) -> None:
    """Clear all changelog entries."""
    log = _get_changelog(store_file)
    log.clear()
    click.echo("Changelog cleared.")
