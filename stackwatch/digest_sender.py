"""Sends a rendered digest via the configured notifier channels."""
from __future__ import annotations

from dataclasses import dataclass

from stackwatch.digest import Digest, render_digest_text
from stackwatch.notifier import Notifier


class DigestSendError(Exception):
    """Raised when digest delivery fails."""


@dataclass
class DigestSender:
    notifiers: list[Notifier]

    def send(self, digest: Digest) -> None:
        if not self.notifiers:
            raise DigestSendError("No notifiers configured for digest delivery.")
        text = render_digest_text(digest)
        errors: list[str] = []
        for notifier in self.notifiers:
            try:
                notifier.send_text(text)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(notifier).__name__}: {exc}")
        if errors:
            raise DigestSendError("Digest delivery failed for: " + "; ".join(errors))
