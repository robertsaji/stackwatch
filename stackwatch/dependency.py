"""Stack dependency tracking — record and query inter-stack relationships."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


class DependencyError(Exception):
    """Raised on dependency store failures."""


@dataclass
class DependencyStore:
    path: Path
    _graph: Dict[str, Set[str]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            self._graph = {}
            return
        try:
            raw: Dict[str, List[str]] = json.loads(self.path.read_text())
            self._graph = {k: set(v) for k, v in raw.items()}
        except Exception as exc:  # noqa: BLE001
            raise DependencyError(f"Failed to load dependency store: {exc}") from exc

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            serialisable = {k: sorted(v) for k, v in self._graph.items()}
            self.path.write_text(json.dumps(serialisable, indent=2))
        except Exception as exc:  # noqa: BLE001
            raise DependencyError(f"Failed to save dependency store: {exc}") from exc

    # ------------------------------------------------------------------
    def add(self, stack: str, depends_on: str) -> None:
        """Record that *stack* depends on *depends_on*."""
        self._graph.setdefault(stack, set()).add(depends_on)
        self._save()

    def remove(self, stack: str, depends_on: str) -> None:
        """Remove a single dependency edge."""
        if stack in self._graph:
            self._graph[stack].discard(depends_on)
            if not self._graph[stack]:
                del self._graph[stack]
            self._save()

    def dependencies(self, stack: str) -> List[str]:
        """Return direct dependencies of *stack*."""
        return sorted(self._graph.get(stack, set()))

    def dependents(self, stack: str) -> List[str]:
        """Return stacks that directly depend on *stack*."""
        return sorted(s for s, deps in self._graph.items() if stack in deps)

    def all_stacks(self) -> List[str]:
        """Return every stack that has at least one recorded dependency."""
        return sorted(self._graph.keys())

    def clear(self, stack: str) -> None:
        """Remove all dependency edges for *stack*."""
        self._graph.pop(stack, None)
        self._save()
