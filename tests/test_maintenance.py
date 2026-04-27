"""Tests for stackwatch.maintenance."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from stackwatch.maintenance import MaintenanceError, MaintenanceStore, MaintenanceWindow


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "maintenance.json"


@pytest.fixture()
def store(store_path: Path) -> MaintenanceStore:
    return MaintenanceStore(path=store_path)


def _window(
    stack: str = "my-stack",
    offset_start: int = -1,
    offset_end: int = 1,
) -> MaintenanceWindow:
    now = datetime.now(timezone.utc)
    return MaintenanceWindow(
        stack_name=stack,
        start=now + timedelta(hours=offset_start),
        end=now + timedelta(hours=offset_end),
        reason="planned deploy",
    )


def test_load_returns_empty_when_no_file(store: MaintenanceStore) -> None:
    assert store.all_windows() == []


def test_add_and_list(store: MaintenanceStore) -> None:
    w = _window()
    store.add(w)
    assert len(store.all_windows()) == 1
    assert store.all_windows()[0].stack_name == "my-stack"


def test_add_persists_to_disk(store_path: Path, store: MaintenanceStore) -> None:
    store.add(_window())
    data = json.loads(store_path.read_text())
    assert len(data) == 1


def test_add_raises_when_end_before_start(store: MaintenanceStore) -> None:
    w = _window(offset_start=1, offset_end=-1)
    with pytest.raises(MaintenanceError, match="end must be after start"):
        store.add(w)


def test_is_suppressed_active_window(store: MaintenanceStore) -> None:
    store.add(_window("stack-a"))
    assert store.is_suppressed("stack-a") is True


def test_is_suppressed_different_stack(store: MaintenanceStore) -> None:
    store.add(_window("stack-a"))
    assert store.is_suppressed("stack-b") is False


def test_is_suppressed_expired_window(store: MaintenanceStore) -> None:
    w = _window(offset_start=-3, offset_end=-1)
    store._windows.append(w)  # bypass validation to insert expired window
    store._save()
    assert store.is_suppressed("my-stack") is False


def test_active_windows_returns_only_active(store: MaintenanceStore) -> None:
    active = _window("active-stack", offset_start=-1, offset_end=1)
    expired = _window("old-stack", offset_start=-3, offset_end=-2)
    store._windows = [active, expired]
    store._save()
    result = store.active_windows()
    assert len(result) == 1
    assert result[0].stack_name == "active-stack"


def test_remove_deletes_matching_windows(store: MaintenanceStore) -> None:
    store.add(_window("stack-x"))
    store.add(_window("stack-y"))
    removed = store.remove("stack-x")
    assert removed == 1
    names = [w.stack_name for w in store.all_windows()]
    assert "stack-x" not in names
    assert "stack-y" in names


def test_load_raises_on_corrupt_file(store_path: Path) -> None:
    store_path.write_text("not json")
    with pytest.raises(MaintenanceError):
        MaintenanceStore(path=store_path)
