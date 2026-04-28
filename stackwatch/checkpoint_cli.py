"""CLI commands for inspecting and managing run checkpoints."""
from __future__ import annotations

import time
from pathlib import Path

import click

from stackwatch.checkpoint import CheckpointError, CheckpointStore

_DEFAULT_PATH = Path(".stackwatch/checkpoint.json")


def _get_store(path: str) -> CheckpointStore:
    return CheckpointStore(Path(path))


@click.group("checkpoint")
def checkpoint_group() -> None:
    """Manage run checkpoints."""


@checkpoint_group.command("show")
@click.option("--path", default=str(_DEFAULT_PATH), show_default=True)
def show_command(path: str) -> None:
    """Display the latest checkpoint."""
    store = _get_store(path)
    try:
        cp = store.load()
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc

    if cp is None:
        click.echo("No checkpoint found.")
        return

    age = cp.age_seconds
    click.echo(f"Run ID   : {cp.run_id}")
    click.echo(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cp.timestamp))}")
    click.echo(f"Age      : {age:.0f}s")
    click.echo(f"Stacks   : {len(cp.stack_names)} total, {len(cp.drifted_stacks)} drifted")
    if cp.metadata:
        click.echo(f"Metadata : {cp.metadata}")


@checkpoint_group.command("clear")
@click.option("--path", default=str(_DEFAULT_PATH), show_default=True)
def clear_command(path: str) -> None:
    """Remove the stored checkpoint."""
    store = _get_store(path)
    store.clear()
    click.echo("Checkpoint cleared.")
