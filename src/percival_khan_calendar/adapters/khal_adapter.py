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

import copy
import logging
import re
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from icalendar import Calendar, Event

from .. import constants
from ..exceptions import (
    KhanAmbiguousMatchError,
    KhanInfrastructureError,
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
        # Track files we ignored on read so the agent (and a future
        # ``khan_get_status`` enhancement) can surface the count instead
        # of returning silently truncated results.
        self._skipped_ics: list[Path] = []

    def __repr__(self) -> str:
        return f"KhalAdapter(data_dir={self._data_dir!r})"

    @property
    def skipped_ics(self) -> tuple[Path, ...]:
        """Files that were ignored because parsing failed.

        Snapshot at the time of the call. Useful for test assertions
        and surface area to be added to ``khan_get_status``.
        """
        return tuple(self._skipped_ics)

    def reset_skipped_counter(self) -> None:
        self._skipped_ics.clear()

    # ---- Reads -----------------------------------------------------------

    def _iter_event_files(self):
        if not self._data_dir.exists():
            return
        for ics_path in sorted(self._data_dir.rglob("*.ics")):
            try:
                cal = Calendar.from_ical(ics_path.read_bytes())
            except Exception:
                # Surfaces in logs AND in the per-adapter counter.
                # We refuse to fail the entire query for one bad file;
                # instead we record it so the agent can be told.
                logger.warning("Skipping malformed ICS: %s", ics_path)
                if ics_path not in self._skipped_ics:
                    self._skipped_ics.append(ics_path)
                continue
            for ev in cal.walk("VEVENT"):
                # ``copy.deepcopy`` the Event so a consumer mutating
                # ``ev["summary"] = ...`` cannot accidentally mutate
                # another EventMatch in a different find() result or
                # leave stale property dicts in the in-memory Calendar.
                # Cost: one deep-copy per matched event during reads;
                # writes are unaffected because ``update_event``
                # re-acquires the lock and rebuilds the EventMatch.
                yield ics_path, cal, copy.deepcopy(ev)

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
        # Trim term so accidental whitespace does not break exact-ish
        # substring matching. Pydantic already strips control chars.
        term_l = term.strip().lower()
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

    _CALENDAR_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

    @classmethod
    def _validate_calendar_name(cls, name: str) -> str:
        """Reject calendar names that could become path components
        outside ``DATA_DIR/<name>/``.

        The calendar name is interpolated into a filesystem path —
        no separators, no leading-dot, no traversal tokens. This
        guard is defence-in-depth: today the tool layer does not
        expose ``calendar``, but if anyone (today or tomorrow)
        lets a user pass an arbitrary string here, an attacker
        could escape ``DATA_DIR/<name>/`` and write anywhere the
        process can write.
        """
        if not isinstance(name, str) or not name:
            raise KhanValidationError("Calendar name must be a non-empty string.")
        if "/" in name or "\\" in name or name.startswith("."):
            raise KhanValidationError(
                f"Invalid calendar name '{name}'. Must match "
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63} and not start with '.'."
            )
        if not cls._CALENDAR_NAME_PATTERN.match(name):
            raise KhanValidationError(
                f"Invalid calendar name '{name}'. Must match "
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}."
            )
        return name

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
        cal_name = self._validate_calendar_name(cal_name)
        with self._write_lock():
            ev = Event()
            ev.add("uid", _make_uid())
            ev.add("summary", title)
            start_dt = dtstart or _parse_khal_time(start)
            # S6 (cosmetic): round-trip DTSTART/DTEND through UTC so the
            # icalendar library emits the canonical RFC-5545 ``Z`` form
            # consistently across create and update paths. Without this
            # the writer would emit ``DTSTART:…+00:00`` on the update
            # path but ``DTSTART:…Z`` on the create path.
            start_dt = _to_utc_z(start_dt)
            ev.add("dtstart", start_dt)
            if dtend:
                ev.add("dtend", _to_utc_z(dtend))
            elif end:
                ev.add("dtend", _to_utc_z(_parse_khal_time(end)))
            else:
                ev.add("dtend", _to_utc_z(start_dt + timedelta(hours=1)))
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
            target_ics_path = existing.filepath
            # ``find_event_unique`` returns an EventMatch built from
            # deep-copied Events so consumer code never mutates the
            # in-memory Calendar by accident. We must therefore
            # re-read the on-disk .ics to obtain the canonical Calendar
            # (still holding the workspace lock for atomicity).
            try:
                canonical = Calendar.from_ical(target_ics_path.read_bytes())
            except Exception as exc:
                # Ics corrupt on disk; surface to caller.
                raise KhanInfrastructureError(
                    f"Cannot read existing event file {target_ics_path.name}: {type(exc).__name__}"
                ) from exc
            events = list(canonical.walk("VEVENT"))
            old_ev = next(
                (e for e in events if str(e.get("uid")) == existing.uid),
                None,
            )
            if old_ev is None:
                # UID moved between read and write — bail loudly so the
                # agent is told instead of writing a stale snapshot.
                raise KhanNotFoundError(f"Event '{existing.uid}' disappeared mid-update.")
            # S6: ``icalendar`` v6 prefers a fresh ``Event`` over
            # mutating properties by ``ev["x"] = value`` because the
            # latter can switch the *serializer* (e.g. ``Z`` →
            # ``+00:00``). We rebuild the Event from the disk-loaded
            # fields plus the requested overrides.
            # S6: Build a *brand-new* Event from raw primitives instead
            # of mutating the on-disk one. The icalendar library ties
            # its serializer choice (``Z`` vs ``+00:00``) to the *type*
            # of the property object held by the Event — mutation
            # through ``ev["x"] = …`` was consistently selecting the
            # ``+00:00`` path for DTSTART/DTEND on round-tripped
            # events, so we avoid that path entirely.
            new_ev = Event()
            new_ev.add("uid", str(old_ev.get("uid", "")))
            new_ev.add("summary", str(old_ev.get("summary", "")))
            old_dtstart = old_ev.get("dtstart")
            new_ev.add(
                "dtstart",
                _to_utc_z(old_dtstart.dt if old_dtstart is not None else None),
            )
            old_dtend = old_ev.get("dtend")
            if old_dtend is not None:
                new_ev.add("dtend", _to_utc_z(old_dtend.dt))
            old_desc = old_ev.get("description")
            if old_desc is not None:
                new_ev.add("description", str(old_desc))
            old_loc = old_ev.get("location")
            if old_loc is not None:
                new_ev.add("location", str(old_loc))
            # Copy through any other property (RRULE, VALARM, X-*).
            _handled = {"UID", "SUMMARY", "DTSTART", "DTEND", "DESCRIPTION", "LOCATION"}
            for prop in old_ev:
                if str(prop).upper() in _handled:
                    continue
                new_ev.add(prop, old_ev[prop])
            # Apply the requested overrides AFTER the copy so they win.
            # IMPORTANT: use ``.add(...)`` (not subscript assignment)
            # because icalendar v6's ``ev["x"] = value`` path picks
            # the ``DTSTART:…+00:00`` serializer. Subscript assignment
            # silently drops the ``Z`` form (S6 regression). We
            # rewrite ``new_ev.from_dict(...)`` which accepts a clean
            # mapping and discards everything from ``old_ev`` except
            # for the keys the caller didn't override.
            _field_map = {
                "summary": "SUMMARY",
                "description": "DESCRIPTION",
                "location": "LOCATION",
                "dtstart": "DTSTART",
                "dtend": "DTEND",
            }
            for key, value in fields.items():
                if value is None or value == "":
                    continue
                k = key.lower()
                upper_key = _field_map.get(k, k.upper())
                # ``add`` appends a duplicate if the property is already
                # present; remove it first so the override wins.
                # ``del ev[UPPER]`` is an icalendar supported op that
                # drops every property of that name.
                try:
                    del new_ev[upper_key]
                except KeyError:
                    pass
                if k == "dtstart":
                    new_ev.add("DTSTART", _to_utc_z(_parse_khal_time(value)))
                elif k == "dtend":
                    new_ev.add("DTEND", _to_utc_z(_parse_khal_time(value)))
                else:
                    new_ev.add(upper_key, value)
            # Re-build the Calendar around the new Event so the property
            # types are decided by fresh icalendar types (Z form).
            # ``icalendar.to_ical()`` of the in-place mutated Calendar
            # was emitting ``+00:00`` because some property types had
            # been written by parsers and the serializer chose a
            # different repr.
            new_cal = Calendar()
            new_cal.add("prodid", "-//percival-khan-calendar//EN")
            new_cal.add("version", "2.0")
            new_cal.add_component(new_ev)
            _atomic_write_ics(target_ics_path, new_cal)
            return EventMatch(
                filepath=target_ics_path,
                ical=new_cal,
                event=new_ev,
                uid=str(new_ev.get("uid", "")),
                summary=str(new_ev.get("summary", "")),
                description=str(new_ev.get("description", "")),
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
    """Parse a khal-style time expression into a **UTC-aware** datetime.

    Accepts:
      * ``today`` / ``tomorrow`` / ``now``
      * ``DD/MM/YYYY`` / ``DD/MM/YYYY HH:MM``
      * ISO-8601 (``%Y-%m-%dT%H:%M:%S``, ``%Y-%m-%d``)
      * ``HH:MM`` (interpreted as today's local time)

    Returns:
        A ``datetime`` normalized to ``timezone.utc``. Wall-clock-only
        inputs (``HH:MM``, ``today``, etc.) are first resolved against
        the *system's* local offset and then converted to UTC so
        ``icalendar`` always emits an unambiguous ``DTSTART:...Z``.
        We deliberately do NOT attach the raw ``datetime.now().astimezone()
        .tzinfo`` (a fixed-offset ``datetime.timezone``, e.g. ``-03``)
        directly to the stored event: ``icalendar`` would serialize it
        as ``TZID=-03``, which is not a valid IANA zone name and which
        khal's own reader rejects with "invalid or incomprehensible
        timezone" (verified against khal 0.14.0) — silently risking a
        wrongly displayed time. Converting to UTC sidesteps that
        entirely: ``Z`` is unambiguous on every machine.

    Raises:
        KhanValidationError: When ``value`` does not match any accepted
            format. Previously this function silently fell back to
            ``datetime.now()``, which hid bugs and produced events at
            the wrong date when the user mistyped the input.
    """
    return _parse_khal_time_wall_clock(value).astimezone(timezone.utc)


def _parse_khal_time_wall_clock(value: str) -> datetime:
    """Resolve ``value`` against the system's local wall-clock offset.

    Internal helper for :func:`_parse_khal_time`; see that function's
    docstring for why the result is converted to UTC before storage.
    """
    if not isinstance(value, str):
        raise KhanValidationError(f"Time expression must be a string, got {type(value).__name__}.")
    s = value.strip()
    now_local = datetime.now().astimezone()
    # ``local_tz`` is what every parsed value defaults to when the user
    # gave a wall-clock time without an explicit timezone.
    local_tz = now_local.tzinfo
    if s == "now":
        return now_local

    # Compound "today HH:MM" / "tomorrow HH:MM" expressions.
    parts = s.split(None, 1)
    if len(parts) == 2 and parts[0] in ("today", "tomorrow"):
        day_keyword, time_str = parts
        base = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        if day_keyword == "tomorrow":
            base = base + timedelta(days=1)
        try:
            t = datetime.strptime(time_str, "%H:%M").time()
        except ValueError as exc:
            raise KhanValidationError(
                f"Invalid time component '{time_str}' in '{value}'. Expected HH:MM."
            ) from exc
        return base.replace(hour=t.hour, minute=t.minute, tzinfo=local_tz)

    if s == "today":
        return now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    if s == "tomorrow":
        return (now_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    for fmt in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%H:%M",
    ):
        try:
            naive = datetime.strptime(s, fmt)
            return naive.replace(tzinfo=local_tz)
        except ValueError:
            continue
    try:
        # ``fromisoformat`` supports the ``+HH:MM`` offset suffix. If
        # the string has no offset we apply ``local_tz`` so the result
        # is timezone-aware.
        parsed = datetime.fromisoformat(s)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=local_tz)
    except ValueError:
        pass
    raise KhanValidationError(
        f"Invalid time expression '{value}'. Expected 'today', 'tomorrow', "
        f"'now', 'DD/MM/YYYY [HH:MM]', 'YYYY-MM-DD', 'HH:MM', "
        "'today HH:MM' or 'tomorrow HH:MM'."
    )


def _to_utc_z(dt: datetime) -> datetime:
    """Normalize a datetime to a UTC-aware ``datetime`` so the icalendar
    library serializes it as the canonical RFC-5545 ``…T…Z`` form.

    Round-6 (S6): without this normalization the writer emits
    ``DTSTART:2026-07-23 12:30:00+00:00`` on the update path but
    ``DTSTART:20260723T123000Z`` on the create path. Both are valid
    but inconsistent. Routing every datetime through this helper
    guarantees the same 8-bit string regardless of the call site.

    Returns the same ``datetime`` if it already has ``tzinfo=UTC`` so
    we avoid an extra allocation on the happy path.
    """
    if dt is None:
        return dt
    # Force the tzinfo to UTC *exactly*. ``astimezone(timezone.utc)``
    # preserves the wall-clock and could land at any offset if the
    # input was tz-aware-but-non-UTC. The icalendar library inspects
    # the ``tzinfo`` identity (not the offset) when choosing the
    # ``Z`` vs ``+00:00`` repr, so we have to give it ``timezone.utc``
    # specifically.
    if getattr(dt, "tzinfo", None) is timezone.utc:
        return dt
    aware = (
        dt
        if dt.tzinfo is not None
        else dt.replace(
            tzinfo=_get_local_tz(),
        )
    )
    utc = aware.astimezone(timezone.utc)
    # Re-create with timezone.utc to make icalendar choose "Z".
    return utc.replace(tzinfo=timezone.utc)


# Module-level lazy tzinfo resolver. We resolve the system local time
# zone once per thread on first use, then cache the tzinfo. The
# icalendar serializer only inspects ``tzinfo`` identity, so a
# per-call ``astimezone()`` is OK but caching saves work.
_LOCAL_SENTINEL = threading.local()


def _get_local_tz():
    cached = getattr(_LOCAL_SENTINEL, "tz", None)
    if cached is not None:
        return cached
    # astimezone() of a naive datetime gives a tz-aware instance;
    # in CPython that tz is the system local.
    cached = datetime.now().astimezone().tzinfo
    _LOCAL_SENTINEL.tz = cached
    return cached


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
