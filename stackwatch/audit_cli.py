"""CLI commands for viewing the audit log."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.audit import AuditLog

_DEFAULT_PATH = Path(".stackwatch") / "audit.json"


def _get_log(path: str) -> AuditLog:
    return AuditLog(Path(path))


@click.group(name="audit")
def audit_group():
    """Manage the drift audit log."""


@audit_group.command(name="list")
@click.option("--stack", default=None, help="Filter by stack name.")
@click.option("--log-file", default=str(_DEFAULT_PATH), show_default=True)
def list_entries(stack: str, log_file: str):
    """List audit log entries."""
    log = _get_log(log_file)
    entries = log.entries(stack_name=stack)
    if not entries:
        click.echo("No audit entries found.")
        return
    for e in entries:
        drift_info = f"{e.drifted_count} drifted" if e.drifted_count else "in sync"
        note = f" [{e.note}]" if e.note else ""
        click.echo(f"{e.timestamp}  {e.stack_name}  {e.status}  {drift_info}{note}")


@audit_group.command(name="clear")
@click.option("--log-file", default=str(_DEFAULT_PATH), show_default=True)
@click.confirmation_option(prompt="Clear all audit entries?")
def clear_entries(log_file: str):
    """Clear all audit log entries."""
    log = _get_log(log_file)
    log.clear()
    click.echo("Audit log cleared.")
