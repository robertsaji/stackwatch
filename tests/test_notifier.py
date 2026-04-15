"""Unit tests for stackwatch.notifier module."""

from unittest.mock import MagicMock, patch

import pytest

from stackwatch.config import AppConfig, SlackConfig, EmailConfig, AWSConfig
from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.notifier import SlackNotifier, EmailNotifier, build_notifiers, _build_message


@pytest.fixture()
def drifted_result():
    return DriftResult(
        stack_name="prod-stack",
        drift_status="DRIFTED",
        drifted_resources=[
            DriftedResource("MyBucket", "AWS::S3::Bucket", "MODIFIED")
        ],
    )


@pytest.fixture()
def in_sync_result():
    return DriftResult(stack_name="prod-stack", drift_status="IN_SYNC")


def test_build_message_contains_stack_name(drifted_result):
    msg = _build_message(drifted_result)
    assert "prod-stack" in msg
    assert "MyBucket" in msg


def test_slack_notifier_sends_on_drift(drifted_result):
    with patch("stackwatch.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        notifier = SlackNotifier("https://hooks.slack.com/test", "#alerts")
        notifier.send(drifted_result)
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert payload["channel"] == "#alerts"
        assert "prod-stack" in payload["text"]


def test_slack_notifier_skips_in_sync(in_sync_result):
    with patch("stackwatch.notifier.requests.post") as mock_post:
        notifier = SlackNotifier("https://hooks.slack.com/test", "#alerts")
        notifier.send(in_sync_result)
        mock_post.assert_not_called()


def test_email_notifier_sends_on_drift(drifted_result):
    with patch("stackwatch.notifier.smtplib.SMTP") as mock_smtp:
        server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        notifier = EmailNotifier("localhost", 25, "from@example.com", ["to@example.com"])
        notifier.send(drifted_result)
        server.sendmail.assert_called_once()


def test_build_notifiers_slack_only():
    config = AppConfig(
        aws=AWSConfig(region="us-east-1"),
        slack=SlackConfig(webhook_url="https://hooks.slack.com/x", channel="#ops"),
    )
    notifiers = build_notifiers(config)
    assert len(notifiers) == 1
    assert isinstance(notifiers[0], SlackNotifier)


def test_build_notifiers_empty_when_no_config():
    config = AppConfig(aws=AWSConfig(region="us-east-1"))
    notifiers = build_notifiers(config)
    assert notifiers == []
