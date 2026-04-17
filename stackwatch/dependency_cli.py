"""CLI commands for managing stack dependencies."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.dependency import DependencyStore

_DEFAULT_PATH = Path(".stackwatch/dependencies.json")


def _get_store(store_file: str) -> DependencyStore:
    return DependencyStore(path=Path(store_file))


@click.group("dependency")
def dependency_group() -> None:
    """Manage inter-stack dependency relationships."""


@dependency_group.command("add")
@click.argument("stack")
@click.argument("depends_on")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def add_dep(stack: str, depends_on: str, store: str) -> None:
    """Record that STACK depends on DEPENDS_ON."""
    _get_store(store).add(stack, depends_on)
    click.echo(f"Added: {stack} -> {depends_on}")


@dependency_group.command("remove")
@click.argument("stack")
@click.argument("depends_on")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def remove_dep(stack: str, depends_on: str, store: str) -> None:
    """Remove a dependency edge."""
    _get_store(store).remove(stack, depends_on)
    click.echo(f"Removed: {stack} -> {depends_on}")


@dependency_group.command("list")
@click.argument("stack")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def list_deps(stack: str, store: str) -> None:
    """List dependencies of STACK."""
    deps = _get_store(store).dependencies(stack)
    if not deps:
        click.echo(f"{stack} has no recorded dependencies.")
    else:
        click.echo(f"Dependencies of {stack}:")
        for d in deps:
            click.echo(f"  - {d}")


@dependency_group.command("dependents")
@click.argument("stack")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def list_dependents(stack: str, store: str) -> None:
    """List stacks that depend on STACK."""
    dependents = _get_store(store).dependents(stack)
    if not dependents:
        click.echo(f"No stacks depend on {stack}.")
    else:
        click.echo(f"Stacks depending on {stack}:")
        for d in dependents:
            click.echo(f"  - {d}")
