"""Baseline management for CloudFormation stack drift results.

Allows saving and comparing drift results against a known-good baseline,
so only new or changed drift is reported.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from stackwatch.drift import DriftResult, DriftedResource


class BaselineError(Exception):
    """Raised when baseline operations fail."""


def _result_to_dict(result: DriftResult) -> dict:
    return {
        "stack_name": result.stack_name,
        "drifted": result.drifted,
        "resources": [
            {
                "logical_id": r.logical_id,
                "resource_type": r.resource_type,
                "drift_status": r.drift_status,
            }
            for r in result.resources
        ],
    }


def _result_from_dict(data: dict) -> DriftResult:
    resources = [
        DriftedResource(
            logical_id=r["logical_id"],
            resource_type=r["resource_type"],
            drift_status=r["drift_status"],
        )
        for r in data.get("resources", [])
    ]
    return DriftResult(
        stack_name=data["stack_name"],
        drifted=data["drifted"],
        resources=resources,
    )


class DriftBaseline:
    """Persists a baseline snapshot of drift results and computes deltas."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def save(self, results: List[DriftResult]) -> None:
        """Persist results as the new baseline."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {r.stack_name: _result_to_dict(r) for r in results}
            self._path.write_text(json.dumps(data, indent=2))
        except OSError as exc:
            raise BaselineError(f"Failed to save baseline: {exc}") from exc

    def load(self) -> Dict[str, DriftResult]:
        """Load the persisted baseline. Returns empty dict if none exists."""
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text())
            return {k: _result_from_dict(v) for k, v in data.items()}
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise BaselineError(f"Failed to load baseline: {exc}") from exc

    def new_drift(self, results: List[DriftResult]) -> List[DriftResult]:
        """Return results that have more drift than the saved baseline."""
        baseline = self.load()
        new: List[DriftResult] = []
        for result in results:
            if not result.drifted:
                continue
            prior = baseline.get(result.stack_name)
            if prior is None:
                new.append(result)
                continue
            prior_ids = {r.logical_id for r in prior.resources}
            current_ids = {r.logical_id for r in result.resources}
            if current_ids - prior_ids:
                new.append(result)
        return new
