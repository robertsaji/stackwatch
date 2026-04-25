"""Drift result archiver — compress and store historical drift snapshots."""
from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from stackwatch.drift import DriftResult
from stackwatch.snapshot import Snapshot


class ArchiveError(Exception):
    """Raised when an archive operation fails."""


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class ArchiveEntry:
    timestamp: str
    filename: str
    stack_count: int
    drifted_count: int

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "filename": self.filename,
            "stack_count": self.stack_count,
            "drifted_count": self.drifted_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchiveEntry":
        return cls(
            timestamp=data["timestamp"],
            filename=data["filename"],
            stack_count=data["stack_count"],
            drifted_count=data["drifted_count"],
        )


@dataclass
class DriftArchiver:
    archive_dir: Path
    index_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.archive_dir = Path(self.archive_dir)
        self.index_file = self.archive_dir / "index.json"

    def _load_index(self) -> List[ArchiveEntry]:
        if not self.index_file.exists():
            return []
        try:
            data = json.loads(self.index_file.read_text())
            return [ArchiveEntry.from_dict(e) for e in data]
        except (json.JSONDecodeError, KeyError) as exc:
            raise ArchiveError(f"Corrupt archive index: {exc}") from exc

    def _save_index(self, entries: List[ArchiveEntry]) -> None:
        _ensure_dir(self.archive_dir)
        self.index_file.write_text(json.dumps([e.to_dict() for e in entries], indent=2))

    def archive(self, snapshot: Snapshot) -> ArchiveEntry:
        """Compress and store a snapshot; return the new index entry."""
        _ensure_dir(self.archive_dir)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"snapshot_{ts}.json.gz"
        dest = self.archive_dir / filename
        payload = json.dumps(snapshot.to_dict()).encode()
        with gzip.open(dest, "wb") as fh:
            fh.write(payload)
        drifted = len(snapshot.drifted())
        entry = ArchiveEntry(
            timestamp=ts,
            filename=filename,
            stack_count=len(snapshot.stack_names()),
            drifted_count=drifted,
        )
        index = self._load_index()
        index.append(entry)
        self._save_index(index)
        return entry

    def load(self, filename: str) -> Snapshot:
        """Decompress and return a previously archived snapshot."""
        path = self.archive_dir / filename
        if not path.exists():
            raise ArchiveError(f"Archive file not found: {filename}")
        with gzip.open(path, "rb") as fh:
            data = json.loads(fh.read())
        return Snapshot.from_dict(data)

    def list_entries(self) -> List[ArchiveEntry]:
        return self._load_index()
