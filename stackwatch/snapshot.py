"""Point-in-time snapshot of drift results for comparison."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from stackwatch.drift import DriftResult


class SnapshotError(Exception):
    pass


@dataclass
class Snapshot:
    timestamp: float
    results: List[DriftResult] = field(default_factory=list)

    def stack_names(self) -> List[str]:
        return [r.stack_name for r in self.results]

    def drifted(self) -> List[DriftResult]:
        return [r for r in self.results if r.has_drift]


def _result_to_dict(r: DriftResult) -> dict:
    return {
        "stack_name": r.stack_name,
        "has_drift": r.has_drift,
        "resources": [
            {"logical_id": res.logical_id, "resource_type": res.resource_type, "status": res.status}
            for res in r.resources
        ],
    }


def _result_from_dict(d: dict) -> DriftResult:
    from stackwatch.drift import DriftedResource
    resources = [
        DriftedResource(
            logical_id=res["logical_id"],
            resource_type=res["resource_type"],
            status=res["status"],
        )
        for res in d.get("resources", [])
    ]
    return DriftResult(stack_name=d["stack_name"], has_drift=d["has_drift"], resources=resources)


class DriftSnapshot:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def save(self, results: List[DriftResult]) -> Snapshot:
        snapshot = Snapshot(timestamp=time.time(), results=results)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": snapshot.timestamp,
            "results": [_result_to_dict(r) for r in results],
        }
        self._path.write_text(json.dumps(data, indent=2))
        return snapshot

    def load(self) -> Optional[Snapshot]:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text())
            results = [_result_from_dict(d) for d in data.get("results", [])]
            return Snapshot(timestamp=data["timestamp"], results=results)
        except Exception as exc:
            raise SnapshotError(f"Failed to load snapshot: {exc}") from exc

    def diff(self, current: List[DriftResult]) -> Dict[str, str]:
        """Return stacks whose drift status changed since last snapshot."""
        previous = self.load()
        if previous is None:
            return {}
        prev_map = {r.stack_name: r.has_drift for r in previous.results}
        changes: Dict[str, str] = {}
        for r in current:
            prev = prev_map.get(r.stack_name)
            if prev is None:
                changes[r.stack_name] = "new"
            elif prev != r.has_drift:
                changes[r.stack_name] = "drifted" if r.has_drift else "resolved"
        return changes
