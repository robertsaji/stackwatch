"""Tests for stackwatch configuration loading."""

import os
import textwrap
from pathlib import Path

import pytest

from stackwatch.config import AppConfig, load_config


@pytest.fixture
def config_file(tmp_path: Path):
    """Helper that writes a YAML config and returns its path."""
    def _write(content: str) -> str:
        p = tmp_path / "stackwatch.yml"
        p.write_text(textwrap.dedent(content))
        return str(p)
    return _write


def test_load_defaults_when_no_file(tmp_path):
    cfg = load_config(str(tmp_path / "nonexistent.yml"))
    assert isinstance(cfg, AppConfig)
    assert cfg.aws.region == "us-east-1"
    assert cfg.slack is None
    assert cfg.email is None
    assert cfg.poll_interval_seconds == 300


def test_load_aws_section(config_file):
    path = config_file("""
        aws:
          region: eu-west-1
          profile: staging
          stacks:
            - my-app-stack
            - my-db-stack
        poll_interval_seconds: 60
    """)
    cfg = load_config(path)
    assert cfg.aws.region == "eu-west-1"
    assert cfg.aws.profile == "staging"
    assert cfg.aws.stacks == ["my-app-stack", "my-db-stack"]
    assert cfg.poll_interval_seconds == 60


def test_load_slack_section(config_file):
    path = config_file("""
        slack:
          webhook_url: https://hooks.slack.com/services/TEST
          channel: "#alerts"
    """)
    cfg = load_config(path)
    assert cfg.slack is not None
    assert cfg.slack.webhook_url == "https://hooks.slack.com/services/TEST"
    assert cfg.slack.channel == "#alerts"


def test_slack_webhook_env_override(config_file, monkeypatch):
    path = config_file("slack:\n  webhook_url: https://original.example.com")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://override.example.com")
    cfg = load_config(path)
    assert cfg.slack.webhook_url == "https://override.example.com"


def test_load_email_section(config_file):
    path = config_file("""
        email:
          smtp_host: smtp.example.com
          smtp_port: 465
          sender: alerts@example.com
          recipients:
            - ops@example.com
          use_tls: true
    """)
    cfg = load_config(path)
    assert cfg.email is not None
    assert cfg.email.smtp_host == "smtp.example.com"
    assert cfg.email.smtp_port == 465
    assert cfg.email.recipients == ["ops@example.com"]


def test_aws_region_env_override(config_file, monkeypatch):
    path = config_file("aws:\n  region: us-west-2")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    cfg = load_config(path)
    assert cfg.aws.region == "ap-southeast-1"
