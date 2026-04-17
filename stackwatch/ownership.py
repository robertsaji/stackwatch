"""Stack ownership mapping — associate stacks with teams or owners."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from stackwatch.drift import DriftResult


class OwnershipError(Exception):
    """Raised when ownership store operations fail."""


@dataclass
class OwnershipStore:
    path: Path
    _data: Dict[str, str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError as exc:
                raise OwnershipError(f"Invalid ownership file: {exc}") from exc
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def set_owner(self, stack_name: str, owner: str) -> None:
        if not stack_name:
            raise OwnershipError("stack_name must not be empty")
        if not owner:
            raise OwnershipError("owner must not be empty")
        self._data[stack_name] = owner
        self._save()

    def remove_owner(self, stack_name: str) -> None:
        self._data.pop(stack_name, None)
        self._save()

    def get_owner(self, stack_name: str) -> Optional[str]:
        return self._data.get(stack_name)

    def all_owners(self) -> Dict[str, str]:
        return dict(self._data)

    def stacks_for_owner(self, owner: str) -> List[str]:
        return [s for s, o in self._data.items() if o == owner]


def annotate_results(
    results: List[DriftResult], store: OwnershipStore
) -> List[tuple[DriftResult, Optional[str]]]:
    """Pair each DriftResult with its owner (or None)."""
    return [(r, store.get_owner(r.stack_name)) for r in results]
