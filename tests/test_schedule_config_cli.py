"""Tests for stackwatch.schedule_config_cli."""
import pytest
from click.testing import CliRunner
from pathlib import Path

from stackwatch.schedule_config_cli import schedule_config_group
from stackwatch.schedule_config import load_schedule_config


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def store_file(tmp_path) -> Path:
    return tmp_path / "sched.json"


def test_list_empty(runner, store_file):
    result = runner.invoke(schedule_config_group, ["list", "--config-file", str(store_file)])
    assert result.exit_code == 0
    assert "Default interval" in result.output
    assert "no custom rules" in result.output


def test_add_rule(runner, store_file):
    result = runner.invoke(
        schedule_config_group,
        ["add", "prod-*", "600", "--config-file", str(store_file)],
    )
    assert result.exit_code == 0
    cfg = load_schedule_config(store_file)
    assert len(cfg.schedules) == 1
    assert cfg.schedules[0].pattern == "prod-*"
    assert cfg.schedules[0].interval_seconds == 600


def test_add_disabled_rule(runner, store_file):
    runner.invoke(
        schedule_config_group,
        ["add", "dev-*", "300", "--disabled", "--config-file", str(store_file)],
    )
    cfg = load_schedule_config(store_file)
    assert not cfg.schedules[0].enabled


def test_remove_rule(runner, store_file):
    runner.invoke(schedule_config_group, ["add", "prod-*", "600", "--config-file", str(store_file)])
    result = runner.invoke(schedule_config_group, ["remove", "prod-*", "--config-file", str(store_file)])
    assert result.exit_code == 0
    cfg = load_schedule_config(store_file)
    assert cfg.schedules == []


def test_list_shows_rules(runner, store_file):
    runner.invoke(schedule_config_group, ["add", "prod-*", "600", "--config-file", str(store_file)])
    result = runner.invoke(schedule_config_group, ["list", "--config-file", str(store_file)])
    assert "prod-*" in result.output
    assert "600" in result.output
