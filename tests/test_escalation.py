"""Tests for stackwatch.escalation."""
import pytest
from unittest.mock import MagicMock
from stackwatch.severity import SeverityLevel
from stackwatch.escalation import (
    EscalationConfig,
    EscalationRule,
    EscalationManager,
    EscalationError,
)
from stackwatch.drift import DriftResult, DriftedResource


def _make_result(stack_name="my-stack", drifted=0):
    resources = [
        DriftedResource(logical_id=f"R{i}", resource_type="AWS::S3::Bucket",
                        drift_status="MODIFIED", expected={}, actual={})
        for i in range(drifted)
    ]
    return DriftResult(stack_name=stack_name, drift_status="DRIFTED" if drifted else "IN_SYNC",
                       drifted_resources=resources)


@pytest.fixture
def config():
    return EscalationConfig(rules=[
        EscalationRule(min_level=SeverityLevel.MEDIUM, notifier_name="slack"),
        EscalationRule(min_level=SeverityLevel.CRITICAL, notifier_name="pagerduty"),
    ])


@pytest.fixture
def manager(config):
    slack = MagicMock()
    pagerduty = MagicMock()
    return EscalationManager(config=config, notifiers={"slack": slack, "pagerduty": pagerduty})


def test_no_rules_match_low_severity(manager):
    result = _make_result(drifted=0)
    used = manager.handle(result)
    assert used == []
    manager.notifiers["slack"].send.assert_not_called()


def test_medium_drift_notifies_slack(manager):
    result = _make_result(drifted=2)
    used = manager.handle(result)
    assert "slack" in used
    assert "pagerduty" not in used
    manager.notifiers["slack"].send.assert_called_once_with(result)


def test_critical_drift_notifies_both(manager):
    result = _make_result(drifted=10)
    used = manager.handle(result)
    assert "slack" in used
    assert "pagerduty" in used


def test_unknown_notifier_raises(config):
    mgr = EscalationManager(config=config, notifiers={"slack": MagicMock()})
    result = _make_result(drifted=10)
    with pytest.raises(EscalationError, match="pagerduty"):
        mgr.handle(result)


def test_handle_all_returns_mapping(manager):
    results = [_make_result("stack-a", drifted=0), _make_result("stack-b", drifted=2)]
    mapping = manager.handle_all(results)
    assert "stack-a" in mapping
    assert "stack-b" in mapping
    assert mapping["stack-a"] == []
    assert "slack" in mapping["stack-b"]


def test_rules_for_returns_matching(config):
    medium_rules = config.rules_for(SeverityLevel.MEDIUM)
    assert len(medium_rules) == 1
    assert medium_rules[0].notifier_name == "slack"

    critical_rules = config.rules_for(SeverityLevel.CRITICAL)
    assert len(critical_rules) == 2
