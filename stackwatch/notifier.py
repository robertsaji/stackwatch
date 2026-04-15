"""Notification dispatchers for Slack and email alerts."""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Protocol

import requests

from stackwatch.config import AppConfig
from stackwatch.drift import DriftResult

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def send(self, result: DriftResult) -> None:
        ...


def _build_message(result: DriftResult) -> str:
    lines = [f":warning: Stack *{result.stack_name}* has drifted!"]
    for r in result.drifted_resources:
        lines.append(f"  • `{r.logical_id}` ({r.resource_type}) — {r.drift_status}")
    return "\n".join(lines)


class SlackNotifier:
    def __init__(self, webhook_url: str, channel: str):
        self._webhook_url = webhook_url
        self._channel = channel

    def send(self, result: DriftResult) -> None:
        if not result.has_drift:
            return
        payload = {
            "channel": self._channel,
            "text": _build_message(result),
        }
        resp = requests.post(self._webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Slack notification sent for stack %s", result.stack_name)


class EmailNotifier:
    def __init__(self, smtp_host: str, smtp_port: int, sender: str, recipients: list[str]):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._sender = sender
        self._recipients = recipients

    def send(self, result: DriftResult) -> None:
        if not result.has_drift:
            return
        body = _build_message(result).replace("*", "").replace("`", "")
        msg = MIMEText(body)
        msg["Subject"] = f"[stackwatch] Drift detected in {result.stack_name}"
        msg["From"] = self._sender
        msg["To"] = ", ".join(self._recipients)
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.sendmail(self._sender, self._recipients, msg.as_string())
        logger.info("Email notification sent for stack %s", result.stack_name)


def build_notifiers(config: AppConfig) -> list[Notifier]:
    """Construct enabled notifiers from application config."""
    notifiers: list[Notifier] = []
    if config.slack and config.slack.webhook_url:
        notifiers.append(SlackNotifier(config.slack.webhook_url, config.slack.channel))
    if config.email and config.email.smtp_host and config.email.recipients:
        notifiers.append(
            EmailNotifier(
                config.email.smtp_host,
                config.email.smtp_port,
                config.email.sender,
                config.email.recipients,
            )
        )
    return notifiers
