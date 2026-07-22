"""Tests for KhalAdapter (icalendar direct manipulation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from percival_khan_calendar.adapters.khal_adapter import (
    EventMatch,
    KhalAdapter,
)
from percival_khan_calendar.exceptions import (
    KhanAmbiguousMatchError,
    KhanNotFoundError,
)


@pytest.fixture
def adapter_with_dir(isolated_workspace: Path) -> KhalAdapter:
    """Point DATA_DIR inside the isolated workspace."""
    # isolated_workspace itself contains 'data', but the adapter writes
    # to <WORKSPACE_DIR>/<calendar>/<uid>.ics. To make lifecycle/db tests
    # co-exist, we set data_dir explicitly.
    # The adapter default is constants.DATA_DIR.
    return KhalAdapter()


def test_create_event_returns_match(adapter_with_dir):
    a = adapter_with_dir
    m = a.write_event(title="Standup", start="today 10:00")
    assert isinstance(m, EventMatch)
    assert m.summary == "Standup"
    assert m.uid
    assert m.filepath.exists()


def test_create_event_persists_ics(adapter_with_dir):
    a = adapter_with_dir
    m = a.write_event(
        title="Meeting",
        start="today 14:00",
        end="today 15:00",
        description="Quarterly review",
        location="Conf room A",
    )
    raw = m.filepath.read_bytes()
    assert b"Meeting" in raw
    assert b"Quarterly review" in raw
    assert b"Conf room A" in raw


def test_event_uid_is_unique(adapter_with_dir):
    a = adapter_with_dir
    a.write_event(title="A", start="today 10:00")
    b = a.write_event(title="B", start="today 11:00")
    assert a.find_event("A")[0].uid != b.uid


def test_find_event_by_summary(adapter_with_dir):
    a = adapter_with_dir
    a.write_event(title="Dentist", start="tomorrow 09:00")
    a.write_event(title="Dentist Special", start="tomorrow 09:00")
    matches = a.find_event("Dentist")
    assert len(matches) == 2


def test_find_event_by_description(adapter_with_dir):
    a = adapter_with_dir
    a.write_event(
        title="X",
        start="today 10:00",
        description="annual checkup",
    )
    matches = a.find_event("checkup", by="description")
    assert len(matches) == 1
    assert matches[0].summary == "X"


def test_find_event_unique_raises_on_zero(adapter_with_dir):
    a = adapter_with_dir
    with pytest.raises(KhanNotFoundError):
        a.find_event_unique("nothing")


def test_find_event_unique_raises_on_many(adapter_with_dir):
    a = adapter_with_dir
    a.write_event(title="Standup", start="today 09:00")
    a.write_event(title="Standup Daily", start="today 09:00")
    with pytest.raises(KhanAmbiguousMatchError) as exc_info:
        a.find_event_unique("Standup")
    assert exc_info.value.term == "Standup"
    assert len(exc_info.value.matches) == 2


def test_update_event_preserves_uid(adapter_with_dir):
    a = adapter_with_dir
    original = a.write_event(
        title="Original",
        start="today 10:00",
        end="today 11:00",
        location="Office",
    )
    original_uid = original.uid
    updated = a.update_event(
        "Original",
        fields={"summary": "New Title", "location": "Remote"},
    )
    assert updated.uid == original_uid
    assert updated.summary == "New Title"
    matches = a.find_event("New Title")
    assert len(matches) == 1
    # Old title is gone
    assert a.find_event("Original") == []


def test_update_event_preserves_rrule(adapter_with_dir):
    a = adapter_with_dir
    original = a.write_event(
        title="Weekly",
        start="today 10:00",
        recurrence="weekly",
    )
    assert original.event.get("rrule") is not None
    original_uid = original.uid

    a.update_event("Weekly", fields={"summary": "Weekly Meeting"})

    matches = a.find_event("Weekly")
    assert len(matches) == 1
    # UID is preserved
    assert matches[0].uid == original_uid
    # RRULE preserved
    assert matches[0].event.get("rrule") is not None


def test_delete_event(adapter_with_dir):
    a = adapter_with_dir
    a.write_event(title="Throwaway", start="today 10:00")
    assert len(a.find_event("Throwaway")) == 1
    a.delete_event("Throwaway")
    assert a.find_event("Throwaway") == []


def test_delete_event_not_found(adapter_with_dir):
    a = adapter_with_dir
    with pytest.raises(KhanNotFoundError):
        a.delete_event("nope")


def test_update_event_not_found(adapter_with_dir):
    a = adapter_with_dir
    with pytest.raises(KhanNotFoundError):
        a.update_event("nope", fields={"summary": "x"})


def test_atomic_write_creates_then_renames(adapter_with_dir, tmp_path):
    """Verify no leftover .tmp files after a successful write."""
    a = adapter_with_dir
    m = a.write_event(title="Atomic", start="today 12:00")
    # No .tmp files should remain
    leftovers = list(m.filepath.parent.glob("*.tmp"))
    assert leftovers == []
