"""CLI commands for drift trend reporting."""
import click
from stackwatch.history import DriftHistory
from stackwatch.trend import build_trend, render_trend_text


def _get_history(path: str) -> DriftHistory:
    return DriftHistory(path)


@click.group(name="trend")
def trend_group() -> None:
    """Drift trend commands."""


@trend_group.command(name="show")
@click.option("--history-file", default=".stackwatch/history.json", show_default=True)
@click.option("--last", default=0, help="Limit to last N entries (0 = all).")
def show_trend(history_file: str, last: int) -> None:
    """Display drift trend from recorded history."""
    history = _get_history(history_file)
    entries = history.load()
    if not entries:
        click.echo("No history entries found.")
        return
    if last > 0:
        entries = entries[-last:]
    report = build_trend(entries)
    click.echo(render_trend_text(report))


@trend_group.command(name="status")
@click.option("--history-file", default=".stackwatch/history.json", show_default=True)
def show_status(history_file: str) -> None:
    """Print improving / worsening / stable status."""
    history = _get_history(history_file)
    entries = history.load()
    if not entries:
        click.echo("No history entries found.", err=True)
        raise SystemExit(1)
    report = build_trend(entries)
    if report.improving:
        click.echo("IMPROVING")
    elif report.worsening:
        click.echo("WORSENING")
    else:
        click.echo("STABLE")
