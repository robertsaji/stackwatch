"""Stack annotation store — attach free-text notes to stacks."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class AnnotationError(Exception):
    pass


@dataclass
class Annotation:
    stack_name: str
    note: str
    author: str = "unknown"
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "stack_name": self.stack_name,
            "note": self.note,
            "author": self.author,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Annotation":
        return cls(
            stack_name=d["stack_name"],
            note=d["note"],
            author=d.get("author", "unknown"),
            created_at=d.get("created_at", ""),
        )


@dataclass
class AnnotationStore:
    path: Path
    _data: Dict[str, List[dict]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except Exception as exc:
                raise AnnotationError(f"Failed to load annotations: {exc}") from exc
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def add(self, annotation: Annotation) -> None:
        key = annotation.stack_name
        self._data.setdefault(key, [])
        self._data[key].append(annotation.to_dict())
        self._save()

    def get(self, stack_name: str) -> List[Annotation]:
        return [Annotation.from_dict(d) for d in self._data.get(stack_name, [])]

    def remove_all(self, stack_name: str) -> int:
        removed = len(self._data.pop(stack_name, []))
        self._save()
        return removed

    def all_stack_names(self) -> List[str]:
        return list(self._data.keys())
