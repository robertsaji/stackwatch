"""CLI commands for stack coverage reporting."""
from __future__ import annotations

import json
import sys

import boto3
import click

from stackwatch.coverage import build_coverage_report, render_coverage_text
from stackwatch.drift import DriftDetector
from stackwatch.config import load_config


@click.group(name="coverage")
def coverage_group() -> None:
    """Stack monitoring coverage commands."""


@coverage_group.command(name="check")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--output", type=click.Choice(["text", "json"]), default="text", show_default=True)
@click.option("--fail-below", default=None, type=float, help="Exit non-zero if coverage % is below this value.")
def check_command(config_path: str | None, output: str, fail_below: float | None) -> None:
    """Report how many stacks are being monitored vs. all stacks in the account."""
    cfg = load_config(config_path)
    session = boto3.Session(
        region_name=cfg.aws.region,
        profile_name=cfg.aws.profile or None,
    )
    cf = session.client("cloudformation")

    paginator = cf.get_paginator("list_stacks")
    all_names: list[str] = []
    for page in paginator.paginate(StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"]):
        for s in page.get("StackSummaries", []):
            all_names.append(s["StackName"])

    detector = DriftDetector(cfg.aws)
    results = detector.detect_all()

    report = build_coverage_report(all_names, results)

    if output == "json":
        click.echo(
            json.dumps(
                {
                    "total_stacks": report.total_stacks,
                    "monitored_stacks": report.monitored_stacks,
                    "coverage_pct": report.coverage_pct,
                    "unmonitored_stacks": list(report.unmonitored_stacks),
                },
                indent=2,
            )
        )
    else:
        click.echo(render_coverage_text(report))

    if fail_below is not None and report.coverage_pct < fail_below:
        click.echo(
            f"Coverage {report.coverage_pct}% is below threshold {fail_below}%.",
            err=True,
        )
        sys.exit(1)
