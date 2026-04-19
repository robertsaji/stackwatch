"""Runbook link store — attach runbook URLs to stacks."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


class RunbookError(Exception):
    pass


@dataclass
class RunbookStore:
    path: Path
    _data: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError as exc:
                raise RunbookError(f"Invalid runbook store: {exc}") from exc
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def set(self, stack_name: str, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            raise RunbookError(f"Invalid URL: {url!r}")
        self._data[stack_name] = url
        self._save()

    def get(self, stack_name: str) -> Optional[str]:
        return self._data.get(stack_name)

    def remove(self, stack_name: str) -> bool:
        if stack_name not in self._data:
            return False
        del self._data[stack_name]
        self._save()
        return True

    def all(self) -> Dict[str, str]:
        return dict(self._data)
