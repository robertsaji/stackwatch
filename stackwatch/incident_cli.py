"""CLI commands for managing drift incidents."""
from pathlib import Path

import click

from stackwatch.incident import IncidentStore

_DEFAULT_PATH = Path(".stackwatch/incidents.json")


def _get_store(store_file: str) -> IncidentStore:
    return IncidentStore(path=Path(store_file))


@click.group("incident")
def incident_group() -> None:
    """Manage drift incidents."""


@incident_group.command("list")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
@click.option("--open-only", is_flag=True, default=False, help="Show only open incidents.")
def list_incidents(store: str, open_only: bool) -> None:
    """List all incidents."""
    s = _get_store(store)
    incidents = s.all()
    if open_only:
        incidents = [i for i in incidents if i.is_open]
    if not incidents:
        click.echo("No incidents found.")
        return
    for inc in incidents:
        status = "OPEN" if inc.is_open else "CLOSED"
        elapsed = f"{inc.elapsed_hours():.1f}h" if inc.elapsed_hours() is not None else "?"
        click.echo(f"[{status}] {inc.incident_id}  {inc.stack_name}  opened={inc.opened_at[:19]}  elapsed={elapsed}")
        if inc.note:
            click.echo(f"         note: {inc.note}")


@incident_group.command("open")
@click.argument("stack_name")
@click.option("--note", default="", help="Optional note.")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def open_incident(stack_name: str, note: str, store: str) -> None:
    """Open a new incident for a stack."""
    from stackwatch.drift import DriftResult
    s = _get_store(store)
    fake_result = DriftResult(stack_name=stack_name, drifted=True, resources=[])
    inc = s.open_incident(fake_result, note=note)
    click.echo(f"Opened incident {inc.incident_id} for stack '{stack_name}'.")


@incident_group.command("close")
@click.argument("incident_id")
@click.option("--store", default=str(_DEFAULT_PATH), show_default=True)
def close_incident(incident_id: str, store: str) -> None:
    """Close an open incident by ID."""
    from stackwatch.incident import IncidentError
    s = _get_store(store)
    try:
        inc = s.close_incident(incident_id)
        click.echo(f"Closed incident {inc.incident_id} for stack '{inc.stack_name}' after {inc.elapsed_hours():.1f}h.")
    except IncidentError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
