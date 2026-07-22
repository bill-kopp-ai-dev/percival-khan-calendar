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
    KhanValidationError,
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

    def __repr__(self) -> str:
        return f"KhalAdapter(data_dir={self._data_dir!r})"

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

    _SEARCH_FIELDS: tuple[str, ...] = ("summary", "description", "anywhere")

    def find_event(
        self,
        term: str,
        *,
        by: str = "anywhere",
    ) -> list[EventMatch]:
        """Locate events matching ``term`` (case-insensitive substring).

        ``by`` may be 'summary', 'description' or 'anywhere' (default).
        An invalid ``by`` raises ``KhanValidationError`` so the adapter
        fails fast instead of leaking ``KeyError`` (regression).
        """
        if by not in self._SEARCH_FIELDS:
            raise KhanValidationError(
                f"Invalid `by` argument: '{by}'. Allowed: {list(self._SEARCH_FIELDS)}."
            )
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
                matches.append(
                    EventMatch(
                        filepath=ics_path,
                        ical=cal,
                        event=ev,
                        uid=str(ev.get("uid", "")),
                        summary=str(ev.get("summary", "")),
                        description=str(ev.get("description", "")),
                    )
                )
        return matches

    def find_event_unique(
        self,
        term: str,
        *,
        by: str = "anywhere",
    ) -> EventMatch:
        matches = self.find_event(term, by=by)
        if not matches:
            raise KhanNotFoundError(f"No event matches '{term}'.")
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
            return _persist_event(cal_name, ev, base_dir=self._data_dir)

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

    def delete_event_safe(self, term: str, *, confirm: bool = False) -> str:
        """Atomic find-and-maybe-delete inside the workspace lock.

        Returns a human-readable message describing the outcome. The
        caller (``tools/delete_event.py``) wraps the result in the
        standard envelope; we keep this adapter API free of LLM-aware
        formatting so it is also usable from CLI scripts.

        Outcomes:
          - 0 matches  → KhanNotFoundError
          - >1 matches → KhanAmbiguousMatchError (refuses; caller
            must narrow the term)
          - 1 match + confirm=False → "DRY-RUN" string with candidates
          - 1 match + confirm=True  → "DELETED <uid>" string

        Raises:
            KhanError subclasses for failure to acquire lock, parse ICS,
            or operate on files.
        """
        # Acquire lock up-front; the find and delete both happen inside
        # it so two concurrent calls cannot see the same event twice.
        with workspace_lock(blocking=True):
            matches = self.find_event(term)
            if len(matches) != 1:
                # Reuse the unique path to surface a typed error to the
                # agent (NotFound or AmbiguousMatch).
                self.find_event_unique(term)
                # The branch above is unreachable since find_event_unique
                # always raises; keeps the explicit assertion for readers.
                raise AssertionError  # pragma: no cover
            m = matches[0]
            if not confirm:
                return (
                    "DRY-RUN\n"
                    f"- UID: {m.uid}\n"
                    f"- Summary: {m.summary}\n"
                    f"- File: {m.filepath.name}\n"
                    "Set confirm=True to actually delete."
                )
            m.filepath.unlink()
            return f"DELETED {m.uid}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uid() -> str:
    """Return a globally-unique event UID."""
    return f"{uuid.uuid4()}@percival-khan-calendar"


def _parse_khal_time(value: str) -> datetime:
    """Parse a khal-style time expression.

    Accepts:
      * ``today`` / ``tomorrow`` / ``now``
      * ``DD/MM/YYYY`` / ``DD/MM/YYYY HH:MM``
      * ISO-8601 (``%Y-%m-%dT%H:%M:%S``, ``%Y-%m-%d``)
      * ``HH:MM`` (interpreted as today's local time)

    Raises:
        KhanValidationError: When ``value`` does not match any accepted
            format. Previously this function silently fell back to
            ``datetime.now()``, which hid bugs and produced events at
            the wrong date when the user mistyped the input.
    """
    if not isinstance(value, str):
        raise KhanValidationError(f"Time expression must be a string, got {type(value).__name__}.")
    s = value.strip()
    now = datetime.now()
    if s == "now":
        return now

    # Compound "today HH:MM" / "tomorrow HH:MM" expressions.
    parts = s.split(None, 1)
    if len(parts) == 2 and parts[0] in ("today", "tomorrow"):
        day_keyword, time_str = parts
        base = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if day_keyword == "tomorrow":
            base = base + timedelta(days=1)
        try:
            t = datetime.strptime(time_str, "%H:%M").time()
        except ValueError as exc:
            raise KhanValidationError(
                f"Invalid time component '{time_str}' in '{value}'. Expected HH:MM."
            ) from exc
        return base.replace(hour=t.hour, minute=t.minute)

    if s == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if s == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

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
        pass
    raise KhanValidationError(
        f"Invalid time expression '{value}'. Expected 'today', 'tomorrow', "
        f"'now', 'DD/MM/YYYY [HH:MM]', 'YYYY-MM-DD', 'HH:MM', "
        "'today HH:MM' or 'tomorrow HH:MM'."
    )


def _to_rrule(value: str):
    """Translate 'daily' / 'weekly' / 'monthly' / 'yearly' to vRecur.

    Raises:
        KhanValidationError: If ``value`` is not in the allowed set
            (this should be unreachable when called via the tool
            layer because Pydantic validates first).
    """
    from icalendar import vRecur

    mapping = {
        "daily": {"freq": "daily"},
        "weekly": {"freq": "weekly"},
        "monthly": {"freq": "monthly"},
        "yearly": {"freq": "yearly"},
    }
    key = value.lower()
    if key not in mapping:
        raise KhanValidationError(f"Invalid recurrence '{value}'. Allowed: {sorted(mapping)}.")
    return vRecur(mapping[key])


def _make_valarm(alarm: str):
    """Build a VALARM sub-component from '15m' / '1h' / '2d' string.

    Raises:
        KhanValidationError: If ``alarm`` does not match the
            ``<int><unit>`` pattern with ``unit in ``s m h d``.
            The Pydantic layer normally catches this first.
    """
    from icalendar import Alarm

    if not isinstance(alarm, str) or len(alarm) < 2:
        raise KhanValidationError(f"Invalid alarm '{alarm}'. Expected like '15m', '1h', '2d'.")
    head, unit = alarm[:-1], alarm[-1].lower()
    if not head.isdigit() or unit not in "smhd":
        raise KhanValidationError(f"Invalid alarm '{alarm}'. Expected like '15m', '1h', '2d'.")
    amount = int(head)
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
    """Write ``.ics`` atomically via tmp + rename + fsync.

    On Linux, ``os.rename`` is atomic on the same filesystem but the
    rename itself is asynchronous and the data may not be on disk yet.
    We ``fsync`` the tmp file **and** the directory so a power loss
    between write and rename cannot leave a partial file in place.
    """
    import os
    import tempfile

    parent = path.parent
    # ``tempfile.NamedTemporaryFile(delete=False)`` avoids colliding
    # with other concurrent writers in different threads.
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(calendar.to_ical())
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    try:
        # Make the directory entry durable.
        dir_fd = os.open(str(parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except (OSError, AttributeError):
        # Directory fsync is not available on all platforms (Windows).
        # Best-effort durability only.
        pass


def _persist_event(
    calendar_name: str,
    event: Event,
    base_dir: Path,
) -> EventMatch:
    """Write a new VEVENT into ``<base_dir>/<calendar>/<uid>.ics``."""
    target_dir = base_dir / calendar_name
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
