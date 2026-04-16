"""CLI commands for generating the drift status page."""
from __future__ import annotations

import click

from stackwatch.config import load_config
from stackwatch.drift import DriftDetector
from stackwatch.exporter import _ensure_dir
from stackwatch.status_page import build_status_page, render_status_html, render_status_text


@click.group(name="status-page")
def status_page_group() -> None:
    """Generate drift status pages."""


@status_page_group.command("show")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def show_command(config_path: str | None) -> None:
    """Print a text status page to stdout."""
    cfg = load_config(config_path)
    detector = DriftDetector(cfg.aws)
    results = detector.detect_all()
    page = build_status_page(results)
    click.echo(render_status_text(page))


@status_page_group.command("export")
@click.argument("output")
@click.option("--format", "fmt", type=click.Choice(["html", "text"]), default="html")
@click.option("--config", "config_path", default=None, help="Path to config file.")
def export_command(output: str, fmt: str, config_path: str | None) -> None:
    """Export the status page to a file."""
    cfg = load_config(config_path)
    detector = DriftDetector(cfg.aws)
    results = detector.detect_all()
    page = build_status_page(results)

    content = render_status_html(page) if fmt == "html" else render_status_text(page)
    _ensure_dir(output)
    with open(output, "w", encoding="utf-8") as fh:
        fh.write(content)
    click.echo(f"Status page written to {output}")
