"""Tests for stackwatch.webhook."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.webhook import WebhookConfig, WebhookError, WebhookNotifier, _build_payload


@pytest.fixture()
def drifted_result() -> DriftResult:
    return DriftResult(
        stack_name="my-stack",
        status="DRIFTED",
        drifted_resources=[
            DriftedResource(
                logical_id="MyBucket",
                resource_type="AWS::S3::Bucket",
                drift_status="MODIFIED",
            )
        ],
    )


@pytest.fixture()
def in_sync_result() -> DriftResult:
    return DriftResult(stack_name="clean-stack", status="IN_SYNC", drifted_resources=[])


@pytest.fixture()
def config() -> WebhookConfig:
    return WebhookConfig(url="https://example.com/hook")


def test_build_payload_contains_stack_name(drifted_result):
    payload = _build_payload(drifted_result)
    assert payload["stack_name"] == "my-stack"


def test_build_payload_contains_resources(drifted_result):
    payload = _build_payload(drifted_result)
    assert len(payload["drifted_resources"]) == 1
    assert payload["drifted_resources"][0]["logical_id"] == "MyBucket"


def test_send_skips_in_sync(config, in_sync_result):
    notifier = WebhookNotifier(config)
    with patch("urllib.request.urlopen") as mock_open:
        notifier.send(in_sync_result)
        mock_open.assert_not_called()


def test_send_posts_on_drift(config, drifted_result):
    notifier = WebhookNotifier(config)
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        notifier.send(drifted_result)  # should not raise


def test_send_raises_webhook_error_on_failure(config, drifted_result):
    import urllib.error
    notifier = WebhookNotifier(config)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        with pytest.raises(WebhookError, match="Webhook delivery failed"):
            notifier.send(drifted_result)
