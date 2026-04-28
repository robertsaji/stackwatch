"""Checkpoint module — persists the last successful run state for recovery."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class CheckpointError(Exception):
    """Raised when checkpoint operations fail."""


@dataclass
class Checkpoint:
    """Represents the state saved at the end of a successful run."""

    run_id: str
    timestamp: float
    stack_names: list[str] = field(default_factory=list)
    drifted_stacks: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "stack_names": self.stack_names,
            "drifted_stacks": self.drifted_stacks,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(
            run_id=data["run_id"],
            timestamp=data["timestamp"],
            stack_names=data.get("stack_names", []),
            drifted_stacks=data.get("drifted_stacks", []),
            metadata=data.get("metadata", {}),
        )

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp


class CheckpointStore:
    """Persists and loads the latest checkpoint from disk."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def save(self, checkpoint: Checkpoint) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(checkpoint.to_dict(), indent=2))
        except OSError as exc:
            raise CheckpointError(f"Failed to save checkpoint: {exc}") from exc

    def load(self) -> Optional[Checkpoint]:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text())
            return Checkpoint.from_dict(data)
        except (json.JSONDecodeError, KeyError) as exc:
            raise CheckpointError(f"Failed to load checkpoint: {exc}") from exc

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
