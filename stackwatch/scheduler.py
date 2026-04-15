"""Scheduler module for periodic drift detection runs."""

import logging
import time
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SchedulerError(Exception):
    """Raised when the scheduler encounters a fatal error."""


class DriftScheduler:
    """Runs drift detection on a configurable interval."""

    def __init__(
        self,
        interval_seconds: int,
        task: Callable[[], None],
        max_runs: Optional[int] = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be a positive integer")
        self.interval_seconds = interval_seconds
        self.task = task
        self.max_runs = max_runs
        self._run_count = 0
        self._running = False

    @property
    def run_count(self) -> int:
        return self._run_count

    def start(self) -> None:
        """Start the scheduler loop. Blocks until stopped or max_runs reached."""
        self._running = True
        logger.info(
            "Scheduler started — interval=%ds max_runs=%s",
            self.interval_seconds,
            self.max_runs,
        )
        try:
            while self._running:
                start_time = datetime.utcnow()
                logger.info("Running drift detection task at %s", start_time.isoformat())
                try:
                    self.task()
                except Exception as exc:  # noqa: BLE001
                    logger.error("Task raised an exception: %s", exc)
                self._run_count += 1
                if self.max_runs is not None and self._run_count >= self.max_runs:
                    logger.info("Reached max_runs=%d, stopping.", self.max_runs)
                    break
                time.sleep(self.interval_seconds)
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal the scheduler to stop after the current sleep."""
        logger.info("Scheduler stop requested.")
        self._running = False
