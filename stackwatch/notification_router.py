"""notification_router.py — Routes drift results to the appropriate notifiers
based on configurable rules (severity, stack pattern, tag, etc.).
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.drift import DriftResult
from stackwatch.notifier import Notifier
from stackwatch.severity import SeverityLevel, classify

logger = logging.getLogger(__name__)


class NotificationRouterError(Exception):
    """Raised when the router is misconfigured or routing fails."""


@dataclass
class RoutingRule:
    """A single routing rule that maps a condition to a list of notifiers.

    Attributes:
        name:            Human-readable label for the rule.
        stack_pattern:   Optional glob pattern matched against the stack name.
        min_severity:    Minimum SeverityLevel required to trigger the rule.
        notifiers:       Notifier instances to invoke when the rule matches.
        enabled:         Whether the rule is active.
    """

    name: str
    notifiers: List[Notifier]
    stack_pattern: Optional[str] = None
    min_severity: SeverityLevel = SeverityLevel.LOW
    enabled: bool = True

    def matches(self, result: DriftResult) -> bool:
        """Return True if *result* satisfies this rule's conditions."""
        if not self.enabled:
            return False

        # Pattern check
        if self.stack_pattern is not None:
            if not fnmatch.fnmatch(result.stack_name, self.stack_pattern):
                return False

        # Severity check — only evaluate drift results that actually drifted
        if result.has_drift:
            severity = classify(result)
            if severity.level.value < self.min_severity.value:
                return False

        return True


@dataclass
class NotificationRouter:
    """Routes a DriftResult to zero or more notifiers based on ordered rules.

    Rules are evaluated in order; *all* matching rules fire (not first-match).
    If no rules are defined a default rule that forwards every drifted result
    to all registered notifiers is used.

    Attributes:
        rules:            Ordered list of RoutingRule objects.
        default_notifiers: Notifiers used when no explicit rules are configured.
    """

    rules: List[RoutingRule] = field(default_factory=list)
    default_notifiers: List[Notifier] = field(default_factory=list)

    def add_rule(self, rule: RoutingRule) -> None:
        """Append *rule* to the routing table."""
        self.rules.append(rule)

    def route(self, result: DriftResult) -> int:
        """Send *result* to every notifier whose rule matches.

        Returns the number of notifications dispatched.
        """
        if not result.has_drift:
            logger.debug("Skipping in-sync stack %s", result.stack_name)
            return 0

        dispatched = 0

        if not self.rules:
            # Fall back to default notifiers
            for notifier in self.default_notifiers:
                try:
                    notifier.send(result)
                    dispatched += 1
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Default notifier %s failed for %s: %s",
                        type(notifier).__name__,
                        result.stack_name,
                        exc,
                    )
            return dispatched

        for rule in self.rules:
            if not rule.matches(result):
                continue
            for notifier in rule.notifiers:
                try:
                    notifier.send(result)
                    dispatched += 1
                    logger.debug(
                        "Rule '%s' dispatched %s for stack %s",
                        rule.name,
                        type(notifier).__name__,
                        result.stack_name,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Notifier %s failed (rule '%s', stack %s): %s",
                        type(notifier).__name__,
                        rule.name,
                        result.stack_name,
                        exc,
                    )

        return dispatched

    def route_all(self, results: List[DriftResult]) -> int:
        """Route every result in *results*; return total notifications sent."""
        return sum(self.route(r) for r in results)
