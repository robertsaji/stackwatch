"""Stack labelling: attach free-form labels to stacks and filter by them."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from stackwatch.drift import DriftResult


class LabelError(Exception):
    """Raised for label store problems."""


@dataclass
class LabelStore:
    path: Path
    _data: Dict[str, List[str]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError as exc:
                raise LabelError(f"Invalid label store: {exc}") from exc
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def set_labels(self, stack_name: str, labels: List[str]) -> None:
        self._data[stack_name] = list(labels)
        self._save()

    def get_labels(self, stack_name: str) -> List[str]:
        return list(self._data.get(stack_name, []))

    def remove(self, stack_name: str) -> None:
        self._data.pop(stack_name, None)
        self._save()

    def all(self) -> Dict[str, List[str]]:
        return dict(self._data)


def filter_by_label(
    results: List[DriftResult],
    store: LabelStore,
    label: str,
) -> List[DriftResult]:
    """Return only results whose stack has *label* attached."""
    return [r for r in results if label in store.get_labels(r.stack_name)]


def group_by_label(
    results: List[DriftResult],
    store: LabelStore,
) -> Dict[str, List[DriftResult]]:
    """Group results by label; a stack may appear under multiple labels."""
    groups: Dict[str, List[DriftResult]] = {}
    for result in results:
        for lbl in store.get_labels(result.stack_name):
            groups.setdefault(lbl, []).append(result)
    return groups
