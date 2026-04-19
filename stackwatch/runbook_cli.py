"""CLI commands for managing runbook links."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.runbook import RunbookError, RunbookStore

_DEFAULT_PATH = Path(".stackwatch/runbooks.json")


def _get_store(store_file: str) -> RunbookStore:
    return RunbookStore(path=Path(store_file))


@click.group("runbook")
def runbook_group() -> None:
    """Manage runbook links for stacks."""


@runbook_group.command("set")
@click.argument("stack_name")
@click.argument("url")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def set_runbook(stack_name: str, url: str, store: str) -> None:
    """Attach a runbook URL to STACK_NAME."""
    try:
        _get_store(store).set(stack_name, url)
        click.echo(f"Runbook set for '{stack_name}'.")
    except RunbookError as exc:
        raise click.ClickException(str(exc))


@runbook_group.command("remove")
@click.argument("stack_name")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def remove_runbook(stack_name: str, store: str) -> None:
    """Remove the runbook link for STACK_NAME."""
    removed = _get_store(store).remove(stack_name)
    if removed:
        click.echo(f"Runbook removed for '{stack_name}'.")
    else:
        click.echo(f"No runbook found for '{stack_name}'.")


@runbook_group.command("list")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def list_runbooks(store: str) -> None:
    """List all runbook links."""
    entries = _get_store(store).all()
    if not entries:
        click.echo("No runbooks configured.")
        return
    for stack, url in sorted(entries.items()):
        click.echo(f"{stack}: {url}")
