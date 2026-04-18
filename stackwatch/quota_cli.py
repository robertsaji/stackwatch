"""CLI commands for quota status inspection."""
from __future__ import annotations
import click
from stackwatch.quota import QuotaConfig, QuotaTracker


_tracker: QuotaTracker | None = None


def _get_tracker(max_per_min: int, max_concurrent: int) -> QuotaTracker:
    global _tracker
    if _tracker is None:
        cfg = QuotaConfig(
            max_detections_per_minute=max_per_min,
            max_concurrent_stacks=max_concurrent,
        )
        _tracker = QuotaTracker(config=cfg)
    return _tracker


@click.group(name="quota")
def quota_group() -> None:
    """Manage and inspect detection quota usage."""


@quota_group.command(name="status")
@click.option("--max-per-min", default=10, show_default=True, help="Max detections per minute.")
@click.option("--max-concurrent", default=20, show_default=True, help="Max concurrent stacks.")
def status_command(max_per_min: int, max_concurrent: int) -> None:
    """Show current quota usage."""
    tracker = _get_tracker(max_per_min, max_concurrent)
    click.echo(f"Used   : {tracker.usage_count()} / {tracker.config.max_detections_per_minute}")
    click.echo(f"Remaining: {tracker.remaining()}")
    stacks = tracker.stacks_detected()
    if stacks:
        click.echo("Recent stacks:")
        for s in stacks:
            click.echo(f"  - {s}")
    else:
        click.echo("No recent detections.")


@quota_group.command(name="reset")
@click.option("--max-per-min", default=10, show_default=True)
@click.option("--max-concurrent", default=20, show_default=True)
def reset_command(max_per_min: int, max_concurrent: int) -> None:
    """Reset the in-memory quota tracker."""
    global _tracker
    _tracker = None
    _get_tracker(max_per_min, max_concurrent)
    click.echo("Quota tracker reset.")
