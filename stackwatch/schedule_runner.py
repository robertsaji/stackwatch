"""Runs drift detection using per-stack schedule configuration."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from stackwatch.drift import DriftResult
from stackwatch.schedule_config import ScheduleConfig, load_schedule_config


@dataclass
class ScheduleRunnerConfig:
    config_path: Path = Path(".stackwatch/schedule_config.json")
    max_runs: int = 0  # 0 = unlimited


class ScheduleRunner:
    """Runs a detect callable per stack respecting per-stack intervals."""

    def __init__(
        self,
        stack_names: List[str],
        detect: Callable[[str], DriftResult],
        on_result: Callable[[DriftResult], None],
        config: ScheduleRunnerConfig,
    ) -> None:
        self._stacks = stack_names
        self._detect = detect
        self._on_result = on_result
        self._config = config
        self._last_run: Dict[str, float] = {}
        self._run_count = 0

    @property
    def run_count(self) -> int:
        return self._run_count

    def _load_schedule(self) -> ScheduleConfig:
        return load_schedule_config(self._config.config_path)

    def _due_stacks(self, schedule: ScheduleConfig, now: float) -> List[str]:
        due = []
        for name in self._stacks:
            interval = schedule.interval_for(name)
            if interval is None:
                continue
            last = self._last_run.get(name, 0.0)
            if now - last >= interval:
                due.append(name)
        return due

    def tick(self) -> List[DriftResult]:
        """Run one tick: detect all due stacks and return results."""
        now = time.monotonic()
        schedule = self._load_schedule()
        results = []
        for name in self._due_stacks(schedule, now):
            result = self._detect(name)
            self._last_run[name] = now
            self._on_result(result)
            results.append(result)
        self._run_count += 1
        return results

    def start(self, sleep_seconds: float = 30.0) -> None:
        """Block and run ticks indefinitely (or up to max_runs)."""
        while True:
            self.tick()
            if self._config.max_runs and self._run_count >= self._config.max_runs:
                break
            time.sleep(sleep_seconds)
