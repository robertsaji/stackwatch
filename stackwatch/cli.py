"""CLI entry-point for stackwatch."""
from __future__ import annotations

import click

from stackwatch.config import load_config
from stackwatch.drift import DriftDetector
from stackwatch.exporter import export_html, export_json, export_text
from stackwatch.notifier import SlackNotifier
from stackwatch.reporter import build_report
from stackwatch.scheduler import DriftScheduler


def _build_task(config):
    detector = DriftDetector(config.aws)
    notifier = SlackNotifier(config.slack) if config.slack else None

    def task():
        results = detector.detect_all()
        if notifier:
            for result in results:
                notifier.send(result)

    return task


@click.group()
def cli():
    """StackWatch — monitor CloudFormation stack drift."""


@cli.command("run")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--interval", default=0, help="Repeat every N seconds (0 = once).")
@click.option("--max-runs", default=None, type=int, help="Stop after N runs.")
@click.option("--export-text", "text_out", default=None, help="Write text report here.")
@click.option("--export-html", "html_out", default=None, help="Write HTML report here.")
@click.option("--export-json", "json_out", default=None, help="Write JSON report here.")
def run_command(config_path, interval, max_runs, text_out, html_out, json_out):
    """Detect drift and optionally export a report."""
    config = load_config(config_path)
    detector = DriftDetector(config.aws)
    notifier = SlackNotifier(config.slack) if config.slack else None

    def task():
        results = detector.detect_all()
        report = build_report(results)
        if notifier:
            for result in results:
                notifier.send(result)
        if text_out:
            export_text(report, text_out)
            click.echo(f"Text report written to {text_out}")
        if html_out:
            export_html(report, html_out)
            click.echo(f"HTML report written to {html_out}")
        if json_out:
            export_json(report, json_out)
            click.echo(f"JSON report written to {json_out}")
        click.echo(
            f"Checked {report.total_stacks} stack(s); "
            f"{report.drifted_stacks} drifted."
        )

    if interval > 0:
        scheduler = DriftScheduler(task, interval_seconds=interval, max_runs=max_runs)
        scheduler.start()
    else:
        task()
