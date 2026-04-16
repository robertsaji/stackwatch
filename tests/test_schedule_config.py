"""Tests for stackwatch.schedule_config."""
import json
import pytest
from pathlib import Path

from stackwatch.schedule_config import (
    ScheduleConfig,
    ScheduleConfigError,
    StackSchedule,
    load_schedule_config,
    save_schedule_config,
)


@pytest.fixture
def cfg_path(tmp_path) -> Path:
    return tmp_path / "sched.json"


def test_load_returns_defaults_when_missing(cfg_path):
    cfg = load_schedule_config(cfg_path)
    assert cfg.default_interval_seconds == 3600
    assert cfg.schedules == []


def test_load_raises_on_invalid_json(cfg_path):
    cfg_path.write_text("not json")
    with pytest.raises(ScheduleConfigError):
        load_schedule_config(cfg_path)


def test_save_and_load_round_trip(cfg_path):
    cfg = ScheduleConfig(
        schedules=[StackSchedule(pattern="prod-*", interval_seconds=600)],
        default_interval_seconds=1800,
    )
    save_schedule_config(cfg, cfg_path)
    loaded = load_schedule_config(cfg_path)
    assert loaded.default_interval_seconds == 1800
    assert len(loaded.schedules) == 1
    assert loaded.schedules[0].pattern == "prod-*"
    assert loaded.schedules[0].interval_seconds == 600


def test_interval_for_matching_pattern():
    cfg = ScheduleConfig(
        schedules=[StackSchedule(pattern="prod-*", interval_seconds=300)],
        default_interval_seconds=3600,
    )
    assert cfg.interval_for("prod-api") == 300


def test_interval_for_default_when_no_match():
    cfg = ScheduleConfig(
        schedules=[StackSchedule(pattern="prod-*", interval_seconds=300)],
        default_interval_seconds=3600,
    )
    assert cfg.interval_for("staging-api") == 3600


def test_interval_for_disabled_returns_none():
    cfg = ScheduleConfig(
        schedules=[StackSchedule(pattern="dev-*", interval_seconds=300, enabled=False)],
        default_interval_seconds=3600,
    )
    assert cfg.interval_for("dev-service") is None


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "sched.json"
    cfg = ScheduleConfig()
    save_schedule_config(cfg, path)
    assert path.exists()
