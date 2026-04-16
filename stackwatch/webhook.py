"""Generic webhook notifier for CloudFormation drift alerts."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any

from stackwatch.drift import DriftResult


class WebhookError(Exception):
    """Raised when a webhook delivery fails."""


@dataclass
class WebhookConfig:
    url: str
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=lambda: {"Content-Type": "application/json"})
    timeout: int = 10


def _build_payload(result: DriftResult) -> dict[str, Any]:
    return {
        "stack_name": result.stack_name,
        "status": result.status,
        "drifted_resources": [
            {
                "logical_id": r.logical_id,
                "resource_type": r.resource_type,
                "drift_status": r.drift_status,
            }
            for r in result.drifted_resources
        ],
    }


class WebhookNotifier:
    def __init__(self, config: WebhookConfig) -> None:
        self._config = config

    def send(self, result: DriftResult) -> None:
        if not result.has_drift:
            return
        payload = json.dumps(_build_payload(result)).encode()
        req = urllib.request.Request(
            self._config.url,
            data=payload,
            headers=self._config.headers,
            method=self._config.method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout):
                pass
        except urllib.error.URLError as exc:
            raise WebhookError(f"Webhook delivery failed: {exc}") from exc
