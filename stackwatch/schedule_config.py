"""Per-stack schedule configuration for drift checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import fnmatch
import json
from pathlib import Path


class ScheduleConfigError(Exception):
    pass


@dataclass
class StackSchedule:
    pattern: str
    interval_seconds: int
    enabled: bool = True

    def matches(self, stack_name: str) -> bool:
        return fnmatch.fnmatch(stack_name, self.pattern)


@dataclass
class ScheduleConfig:
    schedules: List[StackSchedule] = field(default_factory=list)
    default_interval_seconds: int = 3600

    def interval_for(self, stack_name: str) -> Optional[int]:
        for sched in self.schedules:
            if sched.matches(stack_name):
                if not sched.enabled:
                    return None
                return sched.interval_seconds
        return self.default_interval_seconds


def load_schedule_config(path: Path) -> ScheduleConfig:
    if not path.exists():
        return ScheduleConfig()
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ScheduleConfigError(f"Invalid JSON in {path}: {exc}") from exc
    schedules = [
        StackSchedule(
            pattern=s["pattern"],
            interval_seconds=int(s["interval_seconds"]),
            enabled=s.get("enabled", True),
        )
        for s in data.get("schedules", [])
    ]
    return ScheduleConfig(
        schedules=schedules,
        default_interval_seconds=data.get("default_interval_seconds", 3600),
    )


def save_schedule_config(config: ScheduleConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "default_interval_seconds": config.default_interval_seconds,
        "schedules": [
            {"pattern": s.pattern, "interval_seconds": s.interval_seconds, "enabled": s.enabled}
            for s in config.schedules
        ],
    }
    path.write_text(json.dumps(data, indent=2))
