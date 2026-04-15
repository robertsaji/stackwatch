"""Tests for stackwatch.metrics."""
import pytest
from stackwatch.metrics import (
    Counter,
    MetricsError,
    MetricsRegistry,
    counter,
    reset_all,
    snapshot,
)


# ---------------------------------------------------------------------------
# Counter unit tests
# ---------------------------------------------------------------------------

def test_counter_starts_at_zero():
    c = Counter(name="test")
    assert c.value == 0


def test_counter_increment_default():
    c = Counter(name="test")
    c.increment()
    assert c.value == 1


def test_counter_increment_by_amount():
    c = Counter(name="test")
    c.increment(5)
    assert c.value == 5


def test_counter_negative_increment_raises():
    c = Counter(name="test")
    with pytest.raises(MetricsError):
        c.increment(-1)


def test_counter_reset():
    c = Counter(name="test")
    c.increment(10)
    c.reset()
    assert c.value == 0


# ---------------------------------------------------------------------------
# MetricsRegistry tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> MetricsRegistry:
    return MetricsRegistry()


def test_registry_creates_counter_on_first_access(registry):
    c = registry.counter("runs")
    assert c.name == "runs"
    assert c.value == 0


def test_registry_returns_same_counter_for_same_name(registry):
    c1 = registry.counter("runs")
    c2 = registry.counter("runs")
    assert c1 is c2


def test_registry_snapshot_reflects_increments(registry):
    registry.counter("drift_checks").increment(3)
    registry.counter("alerts_sent").increment(1)
    snap = registry.snapshot()
    assert snap["drift_checks"] == 3
    assert snap["alerts_sent"] == 1


def test_registry_names(registry):
    registry.counter("a")
    registry.counter("b")
    assert set(registry.names()) == {"a", "b"}


def test_registry_reset_all(registry):
    registry.counter("x").increment(7)
    registry.reset_all()
    assert registry.snapshot()["x"] == 0


# ---------------------------------------------------------------------------
# Module-level helper tests
# ---------------------------------------------------------------------------

def test_module_counter_and_snapshot():
    reset_all()
    counter("module_test").increment(2)
    snap = snapshot()
    assert snap["module_test"] == 2
    reset_all()


def test_module_reset_all_clears_values():
    reset_all()
    counter("ephemeral").increment(99)
    reset_all()
    assert snapshot().get("ephemeral", 0) == 0
