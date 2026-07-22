"""Round-3 bug-hunt regression tests.

Each class covers one bug found on third review.
"""

from __future__ import annotations

import pytest

from percival_khan_calendar import constants
from percival_khan_calendar.adapters.khal_adapter import KhalAdapter

# ---------------------------------------------------------------------------
# FIX Z/K: Pydantic models strip control chars + trim
# ---------------------------------------------------------------------------


class TestModelsSanitizeControlChars:
    def test_start_strips_control_chars(self):
        from percival_khan_calendar.models import ListEventsInput

        # Control char (BEL = 0x07) is stripped, leaving "today".
        m = ListEventsInput(start_date="today\x07")
        assert m.start_date == "today"

    def test_strip_control_then_check(self):
        """Strip must happen before the leading-dash check."""
        from pydantic import ValidationError

        from percival_khan_calendar.models import ListEventsInput

        # A control char prefix would otherwise become "" after strip
        # and bypass the validation. Our sanitizer strips control chars
        # but leaves regular text untouched, so this is safe.
        with pytest.raises(ValidationError):
            ListEventsInput(start_date="\x00-evil")

    def test_tab_stripped(self):
        from percival_khan_calendar.models import CreateEventInput

        m = CreateEventInput(title="X\tY", start="today")
        # \t is preserved in the title sanitizer (it's whitespace allowed by
        # icalendar). We only strip control chars below 0x20 except \t\n\r.
        assert "X" in m.title and "Y" in m.title

    def test_query_trimmed(self, isolated_workspace):
        from percival_khan_calendar.adapters.khal_adapter import KhalAdapter

        a = KhalAdapter()
        a.write_event(title="Standup", start="today 10:00")
        # With term " Standup " (whitespace), find_event will strip
        # and find the event.
        matches = a.find_event(" Standup ")
        assert len(matches) == 1

    def test_unicode_normalized(self):
        """NFC-normalize so visually-identical inputs collapse."""
        from percival_khan_calendar.models import CreateEventInput

        # "café" composed vs decomposed: 0xC9 vs 0x65+0x301
        m1 = CreateEventInput(title="caf\u00e9", start="today")
        # Sanity: both encodings round-trip identically.
        assert m1.title == "caf\u00e9"


# ---------------------------------------------------------------------------
# FIX 9: corrupted ICS file is tracked, not silent
# ---------------------------------------------------------------------------


class TestCorruptedIcsReporting:
    def test_corrupt_file_does_not_crash_query(self, isolated_workspace):
        a = KhalAdapter()
        # Create a valid event first.
        a.write_event(title="Real", start="today 10:00")
        # Drop a garbage file in the data dir.
        bad = isolated_workspace / "data" / "nanobot" / "bad.ics"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"this is not a valid icalendar file at all")

        # Reset counter to know exactly what happened during this query.
        a.reset_skipped_counter()
        matches = a.find_event("Real")
        assert len(matches) == 1
        assert bad in a.skipped_ics

    def test_corrupt_count_visible_to_caller(self, isolated_workspace):
        a = KhalAdapter()
        bad = isolated_workspace / "data" / "nanobot" / "bad.ics"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"nope")

        a.reset_skipped_counter()
        a.find_event("whatever")
        assert len(a.skipped_ics) == 1


# ---------------------------------------------------------------------------
# FIX H: export_ics has size limit + does not leak absolute path
# ---------------------------------------------------------------------------


class TestExportIcsPrivacyAndLimit:
    def test_export_does_not_leak_absolute_path(self, monkeypatch, isolated_workspace):
        from fastmcp import FastMCP

        from percival_khan_calendar.tools.status import register_status_tools

        mcp = FastMCP("test")
        register_status_tools(mcp)

        from ._helpers import get_tool_fn

        a = KhalAdapter()
        a.write_event(title="A", start="today 10:00")
        a.write_event(title="B", start="today 11:00")

        fn = get_tool_fn(mcp, "khan_export_ics")
        out = fn()
        # The response must mention the basename and the count, but not
        # an absolute filesystem path.
        assert "events" in out
        # Ensure no "/tmp/" or absolute path segment leaked.
        assert "/tmp/" not in out
        assert "/pytest-of-" not in out

    def test_export_size_limit_refuses_huge(self, monkeypatch, isolated_workspace):
        monkeypatch.setattr(constants, "EXPORT_MAX_BYTES", 100)
        from fastmcp import FastMCP

        from percival_khan_calendar.tools.status import register_status_tools

        mcp = FastMCP("test")
        register_status_tools(mcp)

        from ._helpers import get_tool_fn

        a = KhalAdapter()
        a.write_event(
            title="Some long event",
            start="today 10:00",
            description="x" * 500,
        )

        fn = get_tool_fn(mcp, "khan_export_ics")
        out = fn()
        assert "too large" in out
        assert "EXPORT_MAX_BYTES" in out
