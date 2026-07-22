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
    """Verify no leftover .tmp files after a successful write.

    Round-3 follow-up: refined to iterate (rather than glob) so we
    don't pick up ``.tmp`` artefacts from other tooling.
    """
    a = adapter_with_dir
    m = a.write_event(title="Atomic", start="today 12:00")
    # No ``.tmp`` files should remain in this calendar directory. We
    # restrict the search to our ``<DATA_DIR>/<calendar>`` directory
    # to avoid false positives from other test artefacts that might
    # write ``.tmp`` elsewhere (e.g., pytest's own temp files).
    leftovers = [p for p in m.filepath.parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_substring_search_does_not_collide(adapter_with_dir):
    """find_event is a substring search by design; verify that search
    for 'Bar' returns both 'Bar' AND 'Barbecue'. The safety guarantee
    is in *delete_event* / *update_event*, which require a unique match."""
    a = adapter_with_dir
    a.write_event(title="Bar", start="today 12:00")
    a.write_event(title="Barbecue", start="today 13:00")
    matches = a.find_event("Bar")
    # Both events should match because we use substring semantics.
    titles = sorted(m.summary for m in matches)
    assert titles == ["Bar", "Barbecue"]
    # But find_event_unique refuses to disambiguate:
    import pytest

    from percival_khan_calendar.exceptions import KhanAmbiguousMatchError

    with pytest.raises(KhanAmbiguousMatchError):
        a.find_event_unique("Bar")


# ---------------------------------------------------------------------------
# Round-6 follow-up: S5 — path-traversal guard on the ``calendar`` field
# ---------------------------------------------------------------------------


class TestCalendarNameGuard:
    def test_valid_calendar_name_accepted(self, adapter_with_dir):
        a = adapter_with_dir
        # Default nanobot works.
        m = a.write_event(title="X", start="today 10:00", calendar="nanobot")
        assert m.filepath.parent.name == "nanobot"

    def test_path_separator_rejected(self, adapter_with_dir):
        import pytest

        from percival_khan_calendar.exceptions import KhanValidationError

        a = adapter_with_dir
        with pytest.raises(KhanValidationError, match="Invalid calendar name"):
            a.write_event(title="X", start="today 10:00", calendar="../escape")

    def test_backslash_rejected(self, adapter_with_dir):
        a = adapter_with_dir
        import pytest

        from percival_khan_calendar.exceptions import KhanValidationError

        with pytest.raises(KhanValidationError, match="Invalid calendar name"):
            a.write_event(title="X", start="today 10:00", calendar="a\\b")

    def test_leading_dot_rejected(self, adapter_with_dir):
        a = adapter_with_dir
        import pytest

        from percival_khan_calendar.exceptions import KhanValidationError

        with pytest.raises(KhanValidationError, match="Invalid calendar name"):
            a.write_event(title="X", start="today 10:00", calendar=".hidden")

    def test_empty_rejected(self, adapter_with_dir):
        """Calling the adapter directly with ``calendar=""`` falls
        back to ``constants.DEFAULT_CALENDAR`` (``adapter.write_event``
        uses ``calendar or DEFAULT_CALENDAR``). The valid 'nanobot'
        default is accepted.
        """
        a = adapter_with_dir
        m = a.write_event(title="X", start="today 10:00", calendar="")
        # Empty string -> default "nanobot", which is valid.
        assert m.filepath.parent.name == "nanobot"
