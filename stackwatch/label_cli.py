"""CLI commands for managing stack labels."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.label import LabelStore

_DEFAULT_PATH = Path(".stackwatch") / "labels.json"


def _get_store(path: str) -> LabelStore:
    return LabelStore(Path(path))


@click.group("label")
def label_group() -> None:
    """Manage stack labels."""


@label_group.command("set")
@click.argument("stack_name")
@click.argument("labels", nargs=-1, required=True)
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def set_labels(stack_name: str, labels: tuple, store: str) -> None:
    """Attach LABELS to STACK_NAME (replaces existing)."""
    s = _get_store(store)
    s.set_labels(stack_name, list(labels))
    click.echo(f"Labels set for {stack_name}: {', '.join(labels)}")


@label_group.command("remove")
@click.argument("stack_name")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def remove_labels(stack_name: str, store: str) -> None:
    """Remove all labels from STACK_NAME."""
    s = _get_store(store)
    if not s.get_labels(stack_name):
        click.echo(f"No labels found for {stack_name}", err=True)
        raise click.exceptions.Exit(1)
    s.remove(stack_name)
    click.echo(f"Labels removed for {stack_name}")


@label_group.command("list")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def list_labels(store: str) -> None:
    """List all labelled stacks."""
    s = _get_store(store)
    data = s.all()
    if not data:
        click.echo("No labels defined.")
        return
    for stack, labels in sorted(data.items()):
        click.echo(f"{stack}: {', '.join(labels)}")
