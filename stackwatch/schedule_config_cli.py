"""CLI commands for managing per-stack schedule configuration."""
from pathlib import Path

import click

from stackwatch.schedule_config import (
    ScheduleConfig,
    StackSchedule,
    load_schedule_config,
    save_schedule_config,
)

DEFAULT_PATH = Path(".stackwatch/schedule_config.json")


def _get_config(path: str) -> tuple[ScheduleConfig, Path]:
    p = Path(path)
    return load_schedule_config(p), p


@click.group("schedule-config")
def schedule_config_group() -> None:
    """Manage per-stack schedule configuration."""


@schedule_config_group.command("add")
@click.argument("pattern")
@click.argument("interval", type=int)
@click.option("--disabled", is_flag=True, default=False)
@click.option("--config-file", default=str(DEFAULT_PATH))
def add_schedule(pattern: str, interval: int, disabled: bool, config_file: str) -> None:
    """Add or update a schedule rule."""
    cfg, path = _get_config(config_file)
    cfg.schedules = [s for s in cfg.schedules if s.pattern != pattern]
    cfg.schedules.append(StackSchedule(pattern=pattern, interval_seconds=interval, enabled=not disabled))
    save_schedule_config(cfg, path)
    click.echo(f"Added schedule: {pattern} every {interval}s")


@schedule_config_group.command("remove")
@click.argument("pattern")
@click.option("--config-file", default=str(DEFAULT_PATH))
def remove_schedule(pattern: str, config_file: str) -> None:
    """Remove a schedule rule by pattern."""
    cfg, path = _get_config(config_file)
    before = len(cfg.schedules)
    cfg.schedules = [s for s in cfg.schedules if s.pattern != pattern]
    save_schedule_config(cfg, path)
    removed = before - len(cfg.schedules)
    click.echo(f"Removed {removed} rule(s) matching '{pattern}'")


@schedule_config_group.command("list")
@click.option("--config-file", default=str(DEFAULT_PATH))
def list_schedules(config_file: str) -> None:
    """List all schedule rules."""
    cfg, _ = _get_config(config_file)
    if not cfg.schedules:
        click.echo(f"Default interval: {cfg.default_interval_seconds}s (no custom rules)")
        return
    click.echo(f"Default interval: {cfg.default_interval_seconds}s")
    for s in cfg.schedules:
        status = "enabled" if s.enabled else "disabled"
        click.echo(f"  {s.pattern}: {s.interval_seconds}s [{status}]")
