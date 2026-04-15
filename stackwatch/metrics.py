"""Lightweight in-process metrics collector for StackWatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List


class MetricsError(Exception):
    """Raised when an invalid metrics operation is attempted."""


@dataclass
class Counter:
    name: str
    _value: int = field(default=0, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def increment(self, amount: int = 1) -> None:
        if amount < 0:
            raise MetricsError("Increment amount must be non-negative")
        with self._lock:
            self._value += amount

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0


@dataclass
class MetricsRegistry:
    """Central registry that owns all named counters."""
    _counters: Dict[str, Counter] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def counter(self, name: str) -> Counter:
        """Return (creating if necessary) the counter with *name*."""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name)
            return self._counters[name]

    def snapshot(self) -> Dict[str, int]:
        """Return a point-in-time copy of all counter values."""
        with self._lock:
            return {name: c.value for name, c in self._counters.items()}

    def names(self) -> List[str]:
        with self._lock:
            return list(self._counters.keys())

    def reset_all(self) -> None:
        with self._lock:
            for c in self._counters.values():
                c.reset()


# Module-level default registry so callers can do: metrics.counter("runs").increment()
_default_registry = MetricsRegistry()


def counter(name: str) -> Counter:
    return _default_registry.counter(name)


def snapshot() -> Dict[str, int]:
    return _default_registry.snapshot()


def reset_all() -> None:
    _default_registry.reset_all()
