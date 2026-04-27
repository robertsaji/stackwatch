"""CLI commands for managing notification routing rules."""

from __future__ import annotations

import json
from pathlib import Path

import click

from stackwatch.notification_router import NotificationRouter, RoutingRule

_DEFAULT_RULES_PATH = Path(".stackwatch") / "routing_rules.json"


def _get_router(path: Path) -> NotificationRouter:
    """Load a NotificationRouter from *path*, or return an empty one."""
    router = NotificationRouter()
    if path.exists():
        data = json.loads(path.read_text())
        for entry in data.get("rules", []):
            rule = RoutingRule(
                name=entry["name"],
                stack_pattern=entry.get("stack_pattern"),
                severity=entry.get("severity"),
                channel=entry["channel"],
                enabled=entry.get("enabled", True),
            )
            router.add_rule(rule)
    return router


def _save_router(router: NotificationRouter, path: Path) -> None:
    """Persist routing rules to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rules = [
        {
            "name": r.name,
            "stack_pattern": r.stack_pattern,
            "severity": r.severity,
            "channel": r.channel,
            "enabled": r.enabled,
        }
        for r in router.rules
    ]
    path.write_text(json.dumps({"rules": rules}, indent=2))


@click.group(name="routing")
@click.option(
    "--rules-file",
    default=str(_DEFAULT_RULES_PATH),
    show_default=True,
    help="Path to the routing rules JSON file.",
)
@click.pass_context
def routing_group(ctx: click.Context, rules_file: str) -> None:
    """Manage notification routing rules."""
    ctx.ensure_object(dict)
    ctx.obj["rules_file"] = Path(rules_file)


@routing_group.command("add")
@click.argument("name")
@click.argument("channel")
@click.option("--stack-pattern", default=None, help="Glob pattern to match stack names.")
@click.option("--severity", default=None, help="Severity level to match (low/medium/high/critical).")
@click.option("--disabled", is_flag=True, default=False, help="Create the rule in disabled state.")
@click.pass_context
def add_rule(
    ctx: click.Context,
    name: str,
    channel: str,
    stack_pattern: str | None,
    severity: str | None,
    disabled: bool,
) -> None:
    """Add a new routing rule NAME that sends alerts to CHANNEL."""
    path: Path = ctx.obj["rules_file"]
    router = _get_router(path)

    rule = RoutingRule(
        name=name,
        stack_pattern=stack_pattern,
        severity=severity,
        channel=channel,
        enabled=not disabled,
    )
    router.add_rule(rule)
    _save_router(router, path)
    click.echo(f"Added routing rule '{name}' → {channel}.")


@routing_group.command("remove")
@click.argument("name")
@click.pass_context
def remove_rule(ctx: click.Context, name: str) -> None:
    """Remove the routing rule with the given NAME."""
    path: Path = ctx.obj["rules_file"]
    router = _get_router(path)

    before = len(router.rules)
    router.rules = [r for r in router.rules if r.name != name]
    if len(router.rules) == before:
        click.echo(f"No rule named '{name}' found.", err=True)
        raise SystemExit(1)

    _save_router(router, path)
    click.echo(f"Removed routing rule '{name}'.")


@routing_group.command("list")
@click.pass_context
def list_rules(ctx: click.Context) -> None:
    """List all configured routing rules."""
    path: Path = ctx.obj["rules_file"]
    router = _get_router(path)

    if not router.rules:
        click.echo("No routing rules configured.")
        return

    for rule in router.rules:
        status = "enabled" if rule.enabled else "disabled"
        pattern_info = f"  stack={rule.stack_pattern}" if rule.stack_pattern else ""
        severity_info = f"  severity={rule.severity}" if rule.severity else ""
        click.echo(f"[{status}] {rule.name} → {rule.channel}{pattern_info}{severity_info}")


@routing_group.command("check")
@click.argument("stack_name")
@click.option("--severity", default=None, help="Severity level to test routing for.")
@click.pass_context
def check_rule(ctx: click.Context, stack_name: str, severity: str | None) -> None:
    """Show which channels would receive alerts for STACK_NAME."""
    path: Path = ctx.obj["rules_file"]
    router = _get_router(path)

    channels = router.routes_for(stack_name=stack_name, severity=severity)
    if not channels:
        click.echo(f"No routing rules match stack '{stack_name}'.")
        return

    click.echo(f"Stack '{stack_name}' would route to:")
    for channel in channels:
        click.echo(f"  - {channel}")
