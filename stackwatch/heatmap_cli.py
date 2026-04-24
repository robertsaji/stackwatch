"""CLI commands for the drift heatmap feature."""
from __future__ import annotations

from pathlib import Path

import click

from stackwatch.heatmap import build_heatmap, render_heatmap_text
from stackwatch.history import DriftHistory

_DEFAULT_HISTORY = Path("stackwatch_history.json")


def _get_history(path: Path) -> DriftHistory:
    return DriftHistory(path=path)


@click.group(name="heatmap")
def heatmap_group() -> None:
    """Drift frequency heatmap commands."""


@heatmap_group.command(name="show")
@click.option(
    "--history-file",
    default=str(_DEFAULT_HISTORY),
    show_default=True,
    help="Path to the history JSON file.",
)
@click.option(
    "--top",
    default=0,
    show_default=True,
    help="Show only the N hottest stacks (0 = all).",
)
def show_command(history_file: str, top: int) -> None:
    """Display a drift frequency heatmap."""
    history = _get_history(Path(history_file))
    entries = history.load()
    heatmap = build_heatmap(entries)

    if top > 0:
        from stackwatch.heatmap import Heatmap
        heatmap = Heatmap(cells=heatmap.hottest(top))

    click.echo(render_heatmap_text(heatmap))


@heatmap_group.command(name="hottest")
@click.option(
    "--history-file",
    default=str(_DEFAULT_HISTORY),
    show_default=True,
    help="Path to the history JSON file.",
)
@click.option("-n", default=5, show_default=True, help="Number of stacks to show.")
def hottest_command(history_file: str, n: int) -> None:
    """Show the N stacks with the highest drift rate."""
    history = _get_history(Path(history_file))
    entries = history.load()
    heatmap = build_heatmap(entries)
    hottest = heatmap.hottest(n)

    if not hottest:
        click.echo("No heatmap data available.")
        return

    for cell in hottest:
        click.echo(
            f"{cell.stack_name}: {cell.drift_rate:.1%} ({cell.heat_label})"
        )
