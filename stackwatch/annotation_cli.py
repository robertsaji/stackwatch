"""CLI commands for managing stack annotations."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.annotation import Annotation, AnnotationStore

_DEFAULT_PATH = Path(".stackwatch/annotations.json")


def _get_store(path: str) -> AnnotationStore:
    return AnnotationStore(Path(path))


@click.group("annotation")
def annotation_group() -> None:
    """Manage stack annotations."""


@annotation_group.command("add")
@click.argument("stack_name")
@click.argument("note")
@click.option("--author", default="unknown", show_default=True)
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def add_annotation(stack_name: str, note: str, author: str, store: str) -> None:
    """Add a note to a stack."""
    s = _get_store(store)
    import datetime
    ann = Annotation(
        stack_name=stack_name,
        note=note,
        author=author,
        created_at=datetime.datetime.utcnow().isoformat(),
    )
    s.add(ann)
    click.echo(f"Annotation added to {stack_name}.")


@annotation_group.command("list")
@click.argument("stack_name")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def list_annotations(stack_name: str, store: str) -> None:
    """List annotations for a stack."""
    s = _get_store(store)
    annotations = s.get(stack_name)
    if not annotations:
        click.echo(f"No annotations for {stack_name}.")
        return
    for ann in annotations:
        click.echo(f"[{ann.created_at}] ({ann.author}): {ann.note}")


@annotation_group.command("clear")
@click.argument("stack_name")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def clear_annotations(stack_name: str, store: str) -> None:
    """Remove all annotations for a stack."""
    s = _get_store(store)
    count = s.remove_all(stack_name)
    click.echo(f"Removed {count} annotation(s) from {stack_name}.")
