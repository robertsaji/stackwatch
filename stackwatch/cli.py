"""Entry-point CLI for stackwatch."""

import logging
import sys

import click

from stackwatch.config import load_config
from stackwatch.drift import DriftDetector
from stackwatch.notifier import SlackNotifier
from stackwatch.scheduler import DriftScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _build_task(detector: DriftDetector, notifier: SlackNotifier) -> None:
    """Return a callable that detects drift and notifies."""

    def task() -> None:
        results = detector.detect_all()
        for result in results:
            notifier.send(result)

    return task


@click.group()
def cli() -> None:
    """stackwatch — monitor CloudFormation stack drift."""


@cli.command("run")
@click.option("--config", "config_path", default=None, help="Path to config TOML file.")
@click.option("--once", is_flag=True, default=False, help="Run once and exit.")
def run_command(config_path: str, once: bool) -> None:
    """Start drift monitoring."""
    cfg = load_config(config_path)
    detector = DriftDetector(cfg.aws)
    notifier = SlackNotifier(cfg.slack)
    task = _build_task(detector, notifier)

    if once:
        logger.info("Running single drift check.")
        task()
        return

    scheduler = DriftScheduler(
        interval_seconds=cfg.interval_seconds,
        task=task,
    )
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down.")
        scheduler.stop()
        sys.exit(0)


if __name__ == "__main__":
    cli()
