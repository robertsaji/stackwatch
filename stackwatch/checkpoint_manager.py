"""CheckpointManager — creates checkpoints from DriftResult lists."""
from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from stackwatch.checkpoint import Checkpoint, CheckpointStore
from stackwatch.drift import DriftResult


@dataclass
class CheckpointManagerConfig:
    checkpoint_path: Path = Path(".stackwatch/checkpoint.json")
    extra_metadata: dict = field(default_factory=dict)


class CheckpointManager:
    """Builds and persists a Checkpoint from a list of DriftResults."""

    def __init__(self, config: CheckpointManagerConfig) -> None:
        self._config = config
        self._store = CheckpointStore(config.checkpoint_path)

    def record(self, results: List[DriftResult]) -> Checkpoint:
        """Create and persist a checkpoint from *results*."""
        stack_names = [r.stack_name for r in results]
        drifted = [r.stack_name for r in results if r.drifted]
        cp = Checkpoint(
            run_id=str(uuid.uuid4()),
            timestamp=time.time(),
            stack_names=stack_names,
            drifted_stacks=drifted,
            metadata=dict(self._config.extra_metadata),
        )
        self._store.save(cp)
        return cp

    def latest(self):
        """Return the most recent checkpoint, or None."""
        return self._store.load()

    def clear(self) -> None:
        """Remove the stored checkpoint."""
        self._store.clear()
