"""Tests for stackwatch.mute."""
import pytest
from pathlib import Path
from stackwatch.mute import MuteStore, MuteError


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "mute.json"


@pytest.fixture
def store(store_path: Path) -> MuteStore:
    return MuteStore(store_path)


def test_load_returns_empty_when_no_file(store: MuteStore) -> None:
    assert store.all_muted() == {}


def test_mute_stack(store: MuteStore) -> None:
    store.mute("my-stack")
    assert store.is_muted("my-stack")


def test_mute_with_reason(store: MuteStore) -> None:
    store.mute("my-stack", reason="planned maintenance")
    assert store.reason("my-stack") == "planned maintenance"


def test_unmute_stack(store: MuteStore) -> None:
    store.mute("my-stack")
    store.unmute("my-stack")
    assert not store.is_muted("my-stack")


def test_unmute_noop_when_not_muted(store: MuteStore) -> None:
    store.unmute("ghost-stack")  # should not raise
    assert not store.is_muted("ghost-stack")


def test_persists_to_disk(store_path: Path) -> None:
    s1 = MuteStore(store_path)
    s1.mute("stack-a", reason="test")
    s2 = MuteStore(store_path)
    assert s2.is_muted("stack-a")
    assert s2.reason("stack-a") == "test"


def test_all_muted_returns_all(store: MuteStore) -> None:
    store.mute("stack-a")
    store.mute("stack-b", reason="reason")
    muted = store.all_muted()
    assert set(muted.keys()) == {"stack-a", "stack-b"}


def test_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "mute.json"
    p.write_text("not json")
    with pytest.raises(MuteError):
        MuteStore(p)
