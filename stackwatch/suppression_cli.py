"""CLI commands for managing drift suppression rules."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.suppression import SuppressionRule, SuppressionStore

_DEFAULT_PATH = Path(".stackwatch") / "suppressions.json"


def _get_store(path: Path) -> SuppressionStore:
    store = SuppressionStore(path=path)
    store.load()
    return store


@click.group("suppress")
@click.option("--store", "store_path", default=str(_DEFAULT_PATH), show_default=True, help="Path to suppression store.")
@click.pass_context
def suppress_group(ctx: click.Context, store_path: str) -> None:
    """Manage drift suppression rules."""
    ctx.ensure_object(dict)
    ctx.obj["store_path"] = Path(store_path)


@suppress_group.command("add")
@click.argument("stack_name")
@click.option("--reason", required=True, help="Why this stack is suppressed.")
@click.option("--expires-at", default=None, help="ISO-8601 expiry datetime (UTC).")
@click.pass_context
def add_rule(ctx: click.Context, stack_name: str, reason: str, expires_at: str | None) -> None:
    """Add a suppression rule for STACK_NAME."""
    store = _get_store(ctx.obj["store_path"])
    rule = SuppressionRule(stack_name=stack_name, reason=reason, expires_at=expires_at)
    store.add(rule)
    click.echo(f"Suppression added for '{stack_name}'.")


@suppress_group.command("remove")
@click.argument("stack_name")
@click.pass_context
def remove_rule(ctx: click.Context, stack_name: str) -> None:
    """Remove suppression rule for STACK_NAME."""
    store = _get_store(ctx.obj["store_path"])
    if store.remove(stack_name):
        click.echo(f"Suppression removed for '{stack_name}'.")
    else:
        click.echo(f"No suppression found for '{stack_name}'.")


@suppress_group.command("list")
@click.pass_context
def list_rules(ctx: click.Context) -> None:
    """List active suppression rules."""
    store = _get_store(ctx.obj["store_path"])
    rules = store.active_rules()
    if not rules:
        click.echo("No active suppression rules.")
        return
    for rule in rules:
        expiry = rule.expires_at or "permanent"
        click.echo(f"  {rule.stack_name:40s}  expires={expiry:30s}  reason={rule.reason}")
