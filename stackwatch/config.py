"""Configuration management for stackwatch."""

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class SlackConfig:
    webhook_url: str
    channel: Optional[str] = None


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    sender: str
    recipients: list[str] = field(default_factory=list)
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True


@dataclass
class AWSConfig:
    region: str = "us-east-1"
    profile: Optional[str] = None
    stacks: list[str] = field(default_factory=list)  # empty = monitor all


@dataclass
class AppConfig:
    aws: AWSConfig = field(default_factory=AWSConfig)
    slack: Optional[SlackConfig] = None
    email: Optional[EmailConfig] = None
    poll_interval_seconds: int = 300


def load_config(path: str = "stackwatch.yml") -> AppConfig:
    """Load configuration from a YAML file, with env var overrides."""
    raw: dict = {}

    if os.path.exists(path):
        with open(path, "r") as f:
            raw = yaml.safe_load(f) or {}

    aws_raw = raw.get("aws", {})
    aws = AWSConfig(
        region=os.getenv("AWS_DEFAULT_REGION", aws_raw.get("region", "us-east-1")),
        profile=os.getenv("AWS_PROFILE", aws_raw.get("profile")),
        stacks=aws_raw.get("stacks", []),
    )

    slack: Optional[SlackConfig] = None
    slack_raw = raw.get("slack", {})
    webhook = os.getenv("SLACK_WEBHOOK_URL", slack_raw.get("webhook_url"))
    if webhook:
        slack = SlackConfig(
            webhook_url=webhook,
            channel=slack_raw.get("channel"),
        )

    email: Optional[EmailConfig] = None
    email_raw = raw.get("email", {})
    if email_raw.get("smtp_host"):
        email = EmailConfig(
            smtp_host=email_raw["smtp_host"],
            smtp_port=int(email_raw.get("smtp_port", 587)),
            sender=email_raw["sender"],
            recipients=email_raw.get("recipients", []),
            username=os.getenv("SMTP_USERNAME", email_raw.get("username")),
            password=os.getenv("SMTP_PASSWORD", email_raw.get("password")),
            use_tls=email_raw.get("use_tls", True),
        )

    return AppConfig(
        aws=aws,
        slack=slack,
        email=email,
        poll_interval_seconds=int(
            raw.get("poll_interval_seconds", 300)
        ),
    )
