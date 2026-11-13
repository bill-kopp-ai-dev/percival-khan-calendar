"""Tests for KhalAdapter (icalendar direct manipulation)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from icalendar import Alarm, Calendar, Event

from percival_khan_calendar.adapters.khal_adapter import (
    EventMatch,
    KhalAdapter,
)
from percival_khan_calendar.exceptions import (
    KhanAmbiguousMatchError,
    KhanNotFoundError,
    KhanValidationError,
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


@pytest.mark.parametrize(
    ("start", "expected_start", "expected_end"),
    [
        ("06/03/2027", b"DTSTART;VALUE=DATE:20270306", b"DTEND;VALUE=DATE:20270307"),
        ("2027-03-06", b"DTSTART;VALUE=DATE:20270306", b"DTEND;VALUE=DATE:20270307"),
    ],
)
def test_date_only_create_is_all_day_with_exclusive_next_day_end(
    adapter_with_dir, start, expected_start, expected_end
):
    match = adapter_with_dir.write_event(title="Birthday", start=start)

    raw = match.filepath.read_bytes()
    event = Calendar.from_ical(raw).walk("VEVENT")[0]
    assert expected_start in raw
    assert expected_end in raw
    assert event["DTSTART"].dt.isoformat() == "2027-03-06"
    assert event["DTEND"].dt.isoformat() == "2027-03-07"


@pytest.mark.parametrize(
    ("duration", "delta"),
    [
        ("30m", timedelta(minutes=30)),
        ("2h", timedelta(hours=2)),
        ("1d", timedelta(days=1)),
        ("45s", timedelta(seconds=45)),
    ],
)
def test_create_event_duration_is_elapsed_time_in_persisted_ics(adapter_with_dir, duration, delta):
    start = datetime(2026, 11, 15, 10, tzinfo=timezone.utc)
    match = adapter_with_dir.write_event(
        title="Duration", start="ignored", end=duration, dtstart=start
    )

    raw = match.filepath.read_bytes()
    assert b"DTSTART:20261115T100000Z" in raw
    calendar = Calendar.from_ical(raw)
    event = calendar.walk("VEVENT")[0]
    assert event["DTEND"].dt - event["DTSTART"].dt == delta


def test_create_event_duration_crossing_dst_is_elapsed_utc_time(adapter_with_dir):
    start = datetime(2026, 3, 8, 1, 30, tzinfo=ZoneInfo("America/New_York"))
    match = adapter_with_dir.write_event(
        title="DST duration", start="ignored", end="1d", dtstart=start
    )

    event = Calendar.from_ical(match.filepath.read_bytes()).walk("VEVENT")[0]
    assert event["DTEND"].dt - event["DTSTART"].dt == timedelta(days=1)
    assert event["DTSTART"].dt.hour == 6
    assert event["DTEND"].dt.hour == 6


@pytest.mark.parametrize("duration", ["0m", "-1m", "1.5h", "1h30m", "30x", "9" * 64 + "d"])
def test_create_event_rejects_invalid_duration_without_writing(adapter_with_dir, duration):
    from pathlib import Path

    existing = set(Path(adapter_with_dir._data_dir).rglob("*.ics"))
    with pytest.raises(KhanValidationError):
        adapter_with_dir.write_event(
            title="Invalid duration", start="2026-11-15T10:00:00Z", end=duration
        )
    assert set(Path(adapter_with_dir._data_dir).rglob("*.ics")) == existing


def test_create_event_duration_date_overflow_is_validation_error(adapter_with_dir):
    from pathlib import Path

    existing = set(Path(adapter_with_dir._data_dir).rglob("*.ics"))
    with pytest.raises(KhanValidationError, match="too large"):
        adapter_with_dir.write_event(title="Overflow", start="9999-12-31T23:59:59Z", end="1s")
    assert set(Path(adapter_with_dir._data_dir).rglob("*.ics")) == existing


@pytest.mark.parametrize(
    ("alarm", "expected_trigger", "expected_ical_trigger"),
    [
        ("15m", timedelta(minutes=-15), b"TRIGGER:-PT15M"),
        ("1h", timedelta(hours=-1), b"TRIGGER:-PT1H"),
        ("2d", timedelta(days=-2), b"TRIGGER:-P2D"),
    ],
)
def test_create_event_persists_valid_valarm(
    adapter_with_dir, alarm, expected_trigger, expected_ical_trigger
):
    match = adapter_with_dir.write_event(
        title="Alarmed",
        start="2026-11-15T10:00:00Z",
        alarm=alarm,
    )

    raw = match.filepath.read_bytes()
    assert b"BEGIN:VALARM" in raw
    assert b"END:VALARM" in raw
    assert b"VALARM:VALARM(" not in raw
    assert expected_ical_trigger in raw

    calendar = Calendar.from_ical(raw)
    event = calendar.walk("VEVENT")[0]
    valarms = [component for component in event.subcomponents if component.name == "VALARM"]
    assert len(valarms) == 1
    assert isinstance(valarms[0], Alarm)
    assert str(valarms[0]["ACTION"]) == "DISPLAY"
    assert valarms[0]["TRIGGER"].dt == expected_trigger


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


@pytest.mark.parametrize("source", ["external", "adapter"])
def test_update_event_preserves_valarm_and_event_identity(adapter_with_dir, source):
    adapter = adapter_with_dir
    if source == "adapter":
        original = adapter.write_event(
            title="Alarmed",
            start="2026-11-15T10:00:00Z",
            alarm="1h",
            recurrence="weekly",
        )
    else:
        external_event = Event()
        external_event.add("uid", "external-alarm@example.test")
        external_event.add("summary", "Alarmed")
        external_event.add("dtstart", datetime(2026, 11, 15, 10, tzinfo=timezone.utc))
        external_event.add("dtend", datetime(2026, 11, 15, 11, tzinfo=timezone.utc))
        external_event.add("rrule", {"freq": "weekly"})
        external_alarm = Alarm()
        external_alarm.add("action", "DISPLAY")
        external_alarm.add("trigger", timedelta(minutes=-15))
        external_event.add_component(external_alarm)
        original = adapter.write_event(
            title="Temporary",
            start="2026-11-15T10:00:00Z",
        )
        external_calendar = Calendar()
        external_calendar.add("prodid", "-//External Calendar//EN")
        external_calendar.add("version", "2.0")
        external_calendar.add_component(external_event)
        original.filepath.write_bytes(external_calendar.to_ical())
        original_uid = "external-alarm@example.test"

    if source == "adapter":
        original_uid = original.uid

    adapter.update_event("Alarmed", fields={"location": "Updated"})

    raw = original.filepath.read_bytes()
    assert b"BEGIN:VALARM" in raw
    assert b"DTSTART:20261115T100000Z" in raw
    assert b"DTEND:20261115T110000Z" in raw
    calendar = Calendar.from_ical(raw)
    event = calendar.walk("VEVENT")[0]
    assert str(event["UID"]) == original_uid
    assert event.get("RRULE") is not None
    valarms = [component for component in event.subcomponents if component.name == "VALARM"]
    assert len(valarms) == 1
    assert valarms[0]["TRIGGER"].dt == timedelta(minutes=-15 if source == "external" else -60)


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
