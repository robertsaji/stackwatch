"""Tests for stackwatch.watchdog."""
from unittest.mock import MagicMock

import pytest

from stackwatch.watchdog import Watchdog, WatchdogConfig, WatchdogError


@pytest.fixture()
def notifier():
    return MagicMock()


@pytest.fixture()
def cfg():
    return WatchdogConfig(max_consecutive_failures=3, notify_on_recovery=True)


@pytest.fixture()
def dog(cfg, notifier):
    return Watchdog(cfg, notifier)


def test_invalid_max_failures_raises():
    with pytest.raises(WatchdogError):
        WatchdogConfig(max_consecutive_failures=0)


def test_initial_state_is_healthy(dog):
    assert dog.state.is_healthy
    assert dog.state.consecutive_failures == 0


def test_single_failure_does_not_alert(dog, notifier):
    dog.on_failure("timeout")
    notifier.send_text.assert_not_called()
    assert dog.state.consecutive_failures == 1


def test_alert_fires_at_threshold(dog, notifier):
    for i in range(3):
        dog.on_failure(f"error {i}")
    notifier.send_text.assert_called_once()
    assert "Watchdog" in notifier.send_text.call_args[0][0]
    assert dog.state.alerted


def test_alert_fires_only_once_beyond_threshold(dog, notifier):
    for i in range(5):
        dog.on_failure(f"error {i}")
    assert notifier.send_text.call_count == 1


def test_recovery_resets_state(dog, notifier):
    for i in range(3):
        dog.on_failure(f"err {i}")
    dog.on_success()
    assert dog.state.is_healthy
    assert not dog.state.alerted
    assert dog.state.consecutive_failures == 0


def test_recovery_notification_sent(dog, notifier):
    for i in range(3):
        dog.on_failure(f"err {i}")
    notifier.reset_mock()
    dog.on_success()
    notifier.send_text.assert_called_once()
    assert "recovered" in notifier.send_text.call_args[0][0].lower()


def test_no_recovery_notification_when_disabled(notifier):
    cfg = WatchdogConfig(max_consecutive_failures=2, notify_on_recovery=False)
    dog = Watchdog(cfg, notifier)
    for i in range(2):
        dog.on_failure(f"err {i}")
    notifier.reset_mock()
    dog.on_success()
    notifier.send_text.assert_not_called()
