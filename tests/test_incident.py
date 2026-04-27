"""Tests for stackwatch.incident."""
import pytest
from pathlib import Path

from stackwatch.drift import DriftResult
from stackwatch.incident import Incident, IncidentStore, IncidentError


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "incidents.json"


@pytest.fixture()
def store(store_path: Path) -> IncidentStore:
    return IncidentStore(path=store_path)


def _make_result(stack_name: str = "my-stack", drifted: bool = True) -> DriftResult:
    return DriftResult(stack_name=stack_name, drifted=drifted, resources=[])


def test_load_returns_empty_when_no_file(store: IncidentStore) -> None:
    assert store.all() == []


def test_open_incident_creates_entry(store: IncidentStore) -> None:
    result = _make_result("stack-a")
    inc = store.open_incident(result, note="initial drift")
    assert inc.stack_name == "stack-a"
    assert inc.is_open
    assert inc.note == "initial drift"
    assert len(store.all()) == 1


def test_open_incident_persists_to_disk(store: IncidentStore, store_path: Path) -> None:
    store.open_incident(_make_result("stack-b"))
    reloaded = IncidentStore(path=store_path)
    assert len(reloaded.all()) == 1
    assert reloaded.all()[0].stack_name == "stack-b"


def test_close_incident_marks_closed(store: IncidentStore) -> None:
    inc = store.open_incident(_make_result())
    closed = store.close_incident(inc.incident_id)
    assert not closed.is_open
    assert closed.closed_at is not None


def test_close_unknown_incident_raises(store: IncidentStore) -> None:
    with pytest.raises(IncidentError, match="No open incident"):
        store.close_incident("nonexistent")


def test_close_already_closed_raises(store: IncidentStore) -> None:
    inc = store.open_incident(_make_result())
    store.close_incident(inc.incident_id)
    with pytest.raises(IncidentError):
        store.close_incident(inc.incident_id)


def test_open_for_stack_returns_only_open(store: IncidentStore) -> None:
    inc1 = store.open_incident(_make_result("stack-x"))
    store.open_incident(_make_result("stack-y"))
    store.close_incident(inc1.incident_id)
    open_x = store.open_for_stack("stack-x")
    assert open_x == []
    open_y = store.open_for_stack("stack-y")
    assert len(open_y) == 1


def test_elapsed_hours_increases_over_time(store: IncidentStore) -> None:
    inc = store.open_incident(_make_result())
    hours = inc.elapsed_hours()
    assert hours is not None
    assert hours >= 0.0


def test_incident_round_trip_via_dict() -> None:
    inc = Incident(
        incident_id="abc123",
        stack_name="test-stack",
        opened_at="2024-01-01T00:00:00+00:00",
        closed_at="2024-01-01T02:00:00+00:00",
        note="resolved",
    )
    restored = Incident.from_dict(inc.to_dict())
    assert restored.incident_id == inc.incident_id
    assert restored.stack_name == inc.stack_name
    assert not restored.is_open
    assert restored.elapsed_hours() == pytest.approx(2.0, abs=0.01)
