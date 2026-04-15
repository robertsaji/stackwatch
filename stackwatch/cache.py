"""Simple file-based cache for storing previous drift results."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from stackwatch.drift import DriftResult, DriftedResource

DEFAULT_CACHE_PATH = Path(".stackwatch_cache.json")


class CacheError(Exception):
    """Raised when the cache cannot be read or written."""


def _result_to_dict(result: DriftResult) -> dict:
    return {
        "stack_name": result.stack_name,
        "status": result.status,
        "drifted_resources": [
            {
                "logical_id": r.logical_id,
                "resource_type": r.resource_type,
                "drift_status": r.drift_status,
            }
            for r in result.drifted_resources
        ],
    }


def _result_from_dict(data: dict) -> DriftResult:
    resources = [
        DriftedResource(
            logical_id=r["logical_id"],
            resource_type=r["resource_type"],
            drift_status=r["drift_status"],
        )
        for r in data.get("drifted_resources", [])
    ]
    return DriftResult(
        stack_name=data["stack_name"],
        status=data["status"],
        drifted_resources=resources,
    )


class DriftCache:
    """Persists drift results to disk so repeated runs can detect changes."""

    def __init__(self, path: Path = DEFAULT_CACHE_PATH) -> None:
        self.path = path

    def _load_raw(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            with self.path.open() as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            raise CacheError(f"Failed to read cache at {self.path}: {exc}") from exc

    def get(self, stack_name: str) -> Optional[DriftResult]:
        """Return the cached DriftResult for *stack_name*, or None."""
        raw = self._load_raw()
        entry = raw.get(stack_name)
        return _result_from_dict(entry) if entry else None

    def set(self, result: DriftResult) -> None:
        """Persist *result*, overwriting any previous entry for the stack."""
        raw = self._load_raw()
        raw[result.stack_name] = _result_to_dict(result)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w") as fh:
                json.dump(raw, fh, indent=2)
        except OSError as exc:
            raise CacheError(f"Failed to write cache at {self.path}: {exc}") from exc

    def has_changed(self, result: DriftResult) -> bool:
        """Return True if *result* differs from the cached version."""
        previous = self.get(result.stack_name)
        if previous is None:
            return True
        return _result_to_dict(result) != _result_to_dict(previous)
