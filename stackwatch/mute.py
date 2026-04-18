"""Mute/unmute stacks to suppress all alerts for a given stack."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


class MuteError(Exception):
    pass


@dataclass
class MuteStore:
    path: Path
    _data: Dict[str, Optional[str]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError as exc:
                raise MuteError(f"Invalid mute store: {exc}") from exc
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def mute(self, stack_name: str, reason: Optional[str] = None) -> None:
        """Mute a stack, optionally recording a reason."""
        self._data[stack_name] = reason
        self._save()

    def unmute(self, stack_name: str) -> None:
        """Unmute a stack. Raises MuteError if the stack is not muted."""
        if stack_name not in self._data:
            raise MuteError(f"Stack {stack_name!r} is not muted")
        del self._data[stack_name]
        self._save()

    def is_muted(self, stack_name: str) -> bool:
        return stack_name in self._data

    def reason(self, stack_name: str) -> Optional[str]:
        return self._data.get(stack_name)

    def all_muted(self) -> Dict[str, Optional[str]]:
        return dict(self._data)
