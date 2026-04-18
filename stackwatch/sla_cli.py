"""CLI commands for SLA tracking."""
import click
from pathlib import Path
from datetime import datetime
from stackwatch.sla import SLAConfig, SLATracker


def _get_tracker(store_file: str, max_hours: float) -> SLATracker:
    return SLATracker(path=Path(store_file), config=SLAConfig(max_drift_hours=max_hours))


@click.group(name="sla")
def sla_group() -> None:
    """SLA breach tracking commands."""


@sla_group.command(name="status")
@click.option("--store", default=".stackwatch/sla.json", show_default=True)
@click.option("--max-hours", default=24.0, show_default=True)
def status_command(store: str, max_hours: float) -> None:
    """Show SLA status for all tracked stacks."""
    tracker = _get_tracker(store, max_hours)
    statuses = tracker.all_statuses()
    if not statuses:
        click.echo("No drifted stacks being tracked.")
        return
    for s in statuses:
        state = "BREACHED" if s.breached else ("WARNING" if s.warning(tracker.config) else "OK")
        click.echo(f"{s.stack_name}: {state} | elapsed={s.elapsed_hours:.1f}h remaining={s.remaining_hours:.1f}h")


@sla_group.command(name="clear")
@click.argument("stack_name")
@click.option("--store", default=".stackwatch/sla.json", show_default=True)
@click.option("--max-hours", default=24.0, show_default=True)
def clear_command(stack_name: str, store: str, max_hours: float) -> None:
    """Clear SLA record for a resolved stack."""
    tracker = _get_tracker(store, max_hours)
    tracker.clear(stack_name)
    click.echo(f"Cleared SLA record for {stack_name}.")
