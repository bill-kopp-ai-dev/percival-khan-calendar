"""KhalAdapter: abstracts read/write operations over the .ics files.

Preserves UID and RRULE across edits by modifying the canonical
icalendar in place rather than deleting and recreating events.

Why not talk directly to ``khal.db``? The schema is not part of the
public API. Instead, this adapter:

  * reads/writes the ``.ics`` files in the calendar directory,
  * writes each event into ``<WORKSPACE_DIR>/<calendar_name>/<uid>.ics``
    so deletes are idempotent and there are no multi-UID files.

Locking is enforced by :func:`workspace_lock` (no-op when
``ENABLE_LOCK=false``).
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from icalendar import Calendar, Event

from .. import constants
from ..exceptions import (
    KhanAmbiguousMatchError,
    KhanNotFoundError,
)
from .locks import workspace_lock

logger = logging.getLogger("percival-khan-calendar.adapter")


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EventMatch:
    """Result of locating an event in the workspace."""

    filepath: Path
    ical: Calendar
    event: Event
    uid: str
    summary: str
    description: str

    def format(self, *, fmt: Literal["plain", "compact"] = "plain") -> str:
        """Return a single-line representation for the LLM."""
        location = self.filepath.name if self.filepath else "<in-memory>"
        return f"[{self.uid}] {self.summary} ({location})"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class KhalAdapter:
    """Adapter for read/create/update/delete operations.

    Stateless apart from the workspace paths. Each write method acquires
    a workspace lock (no-op when ``ENABLE_LOCK=false``).
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or constants.DATA_DIR

    # ---- Reads -----------------------------------------------------------

    def _iter_event_files(self):
        if not self._data_dir.exists():
            return
        for ics_path in sorted(self._data_dir.rglob("*.ics")):
            try:
                cal = Calendar.from_ical(ics_path.read_bytes())
            except Exception:
                logger.warning("Skipping malformed ICS: %s", ics_path)
                continue
            for ev in cal.walk("VEVENT"):
                yield ics_path, cal, ev

    def find_event(
        self,
        term: str,
        *,
        by: str = "anywhere",
    ) -> list[EventMatch]:
        """Locate events matching ``term`` (case-insensitive substring).

        ``by`` may be 'summary', 'description' or 'anywhere' (default).
        """
        term_l = term.lower()
        matches: list[EventMatch] = []
        for ics_path, cal, ev in self._iter_event_files():
            summary = str(ev.get("summary", "")).lower()
            description = str(ev.get("description", "")).lower()
            haystack = {
                "summary": summary,
                "description": description,
                "anywhere": f"{summary}\n{description}",
            }[by]
            if term_l in haystack:
                matches.append(EventMatch(
                    filepath=ics_path,
                    ical=cal,
                    event=ev,
                    uid=str(ev.get("uid", "")),
                    summary=str(ev.get("summary", "")),
                    description=str(ev.get("description", "")),
                ))
        return matches

    def find_event_unique(
        self,
        term: str,
        *,
        by: str = "anywhere",
    ) -> EventMatch:
        matches = self.find_event(term, by=by)
        if not matches:
            raise KhanNotFoundError(
                f"No event matches '{term}'."
            )
        if len(matches) > 1:
            raise KhanAmbiguousMatchError(
                term=term,
                matches=[m.summary for m in matches],
            )
        return matches[0]

    # ---- Writes ----------------------------------------------------------

    @contextmanager
    def _write_lock(self):
        with workspace_lock(blocking=True):
            yield

    def write_event(
        self,
        *,
        title: str,
        start: str,
        end: str = "",
        description: str = "",
        location: str = "",
        alarm: str = "",
        recurrence: str = "",
        calendar: str | None = None,
        dtstart: datetime | None = None,
        dtend: datetime | None = None,
    ) -> EventMatch:
        """Create a new event.

        Either ``start`` (a free-form khal time string) or ``dtstart``
        (an explicit datetime) must be provided. ``end`` is optional.
        """
        cal_name = calendar or constants.DEFAULT_CALENDAR
        with self._write_lock():
            ev = Event()
            ev.add("uid", _make_uid())
            ev.add("summary", title)
            start_dt = dtstart or _parse_khal_time(start)
            ev.add("dtstart", start_dt)
            if dtend:
                ev.add("dtend", dtend)
            elif end:
                ev.add("dtend", _parse_khal_time(end))
            else:
                ev.add("dtend", start_dt + timedelta(hours=1))
            if description:
                ev.add("description", description)
            if location:
                ev.add("location", location)
            if recurrence:
                ev.add("rrule", _to_rrule(recurrence))
            if alarm:
                ev.add("valarm", _make_valarm(alarm))
            return _persist_event(cal_name, ev)

    def update_event(
        self,
        old_term: str,
        *,
        fields: dict,
    ) -> EventMatch:
        """In-place update preserving UID and RRULE."""
        with self._write_lock():
            existing = self.find_event_unique(old_term)
            ev = existing.event
            for key, value in fields.items():
                if value is None or value == "":
                    continue
                k = key.lower()
                if k == "summary":
                    ev["summary"] = value
                elif k == "description":
                    ev["description"] = value
                elif k == "location":
                    ev["location"] = value
                elif k == "dtstart":
                    ev["dtstart"] = _parse_khal_time(value)
                elif k == "dtend":
                    ev["dtend"] = _parse_khal_time(value)
            _atomic_write_ics(existing.filepath, existing.ical)
            return EventMatch(
                filepath=existing.filepath,
                ical=existing.ical,
                event=ev,
                uid=str(ev.get("uid", "")),
                summary=str(ev.get("summary", "")),
                description=str(ev.get("description", "")),
            )

    def delete_event(self, term: str) -> int:
        """Delete the unique event matching ``term``."""
        with self._write_lock():
            existing = self.find_event_unique(term)
            existing.filepath.unlink()
            return 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uid() -> str:
    """Return a globally-unique event UID."""
    return f"{uuid.uuid4()}@percival-khan-calendar"


def _parse_khal_time(value: str) -> datetime:
    """Best-effort parse of a khal-style time expression.

    Accepts:
      * ``today`` / ``tomorrow``
      * ``DD/MM/YYYY`` / ``DD/MM/YYYY HH:MM``
      * ISO-8601
      * ``HH:MM``
    Falls back to current local time if nothing matches.
    """
    s = value.strip()
    now = datetime.now()
    if s in ("", "now"):
        return now
    if s == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if s == "tomorrow":
        return (
            now + timedelta(days=1)
        ).replace(hour=0, minute=0, second=0, microsecond=0)
    for fmt in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%H:%M",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return now


def _to_rrule(value: str):
    """Translate 'daily' / 'weekly' / 'monthly' / 'yearly' to vRecur."""
    from icalendar import vRecur

    mapping = {
        "daily": {"freq": "daily"},
        "weekly": {"freq": "weekly"},
        "monthly": {"freq": "monthly"},
        "yearly": {"freq": "yearly"},
    }
    return vRecur(mapping[value.lower()])


def _make_valarm(alarm: str):
    """Build a VALARM sub-component from '15m' / '1h' / '2d' string."""
    from icalendar import Alarm

    amount = int(alarm[:-1])
    unit = alarm[-1].lower()
    delta = {
        "s": timedelta(seconds=amount),
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
    }[unit]
    a = Alarm()
    a.add("action", "DISPLAY")
    a.add("trigger", -delta)
    return a


def _atomic_write_ics(path: Path, calendar: Calendar) -> None:
    """Write ``.ics`` atomically via tmp + rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(calendar.to_ical())
    tmp.replace(path)


def _persist_event(
    calendar_name: str,
    event: Event,
) -> EventMatch:
    """Write a new VEVENT into ``<DATA_DIR>/<calendar>/<uid>.ics``."""
    target_dir = constants.DATA_DIR / calendar_name
    target_dir.mkdir(parents=True, exist_ok=True)
    uid = str(event.get("uid", _make_uid()))
    target = target_dir / f"{uid}.ics"

    cal = Calendar()
    cal.add("prodid", "-//percival-khan-calendar//EN")
    cal.add("version", "2.0")
    cal.add_component(event)

    _atomic_write_ics(target, cal)
    return EventMatch(
        filepath=target,
        ical=cal,
        event=event,
        uid=uid,
        summary=str(event.get("summary", "")),
        description=str(event.get("description", "")),
    )


__all__ = ["KhalAdapter", "EventMatch"]
