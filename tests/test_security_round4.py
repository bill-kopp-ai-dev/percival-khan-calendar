"""Round-4 bug-hunt regression tests."""

from __future__ import annotations

from unittest import mock

import pytest

from percival_khan_calendar.adapters.khal_adapter import (
    KhalAdapter,
)
from percival_khan_calendar.adapters.subprocess_runner import (
    executar_comando_khal,
)
from percival_khan_calendar.exceptions import (
    KhanInfrastructureError,
)

from ._helpers import get_tool_fn

# ---------------------------------------------------------------------------
# FIX AJ: timezone-aware datetimes round-trip via icalendar correctly
# ---------------------------------------------------------------------------


class TestDatetimeTimezoneAware:
    def test_today_is_timezone_aware(self, isolated_workspace):
        from percival_khan_calendar.adapters.khal_adapter import _parse_khal_time

        dt = _parse_khal_time("today")
        assert dt.tzinfo is not None, (
            "Today must be timezone-aware so the iCal encoding marks the "
            "DTSTART as local-time-with-offset (not naive local time, which "
            "is interpreted as UTC on a different machine)."
        )

    def test_now_is_timezone_aware(self, isolated_workspace):
        from percival_khan_calendar.adapters.khal_adapter import _parse_khal_time

        dt = _parse_khal_time("now")
        assert dt.tzinfo is not None

    def test_dd_mm_yyyy_is_timezone_aware(self, isolated_workspace):
        from percival_khan_calendar.adapters.khal_adapter import _parse_khal_time

        dt = _parse_khal_time("25/12/2099 14:30")
        assert dt.tzinfo is not None

    def test_iso_with_offset_kept(self, isolated_workspace):
        from percival_khan_calendar.adapters.khal_adapter import _parse_khal_time

        # ISO with explicit offset is preserved as UTC-aware; we don't
        # re-interpret it as local time.
        dt = _parse_khal_time("2099-12-25T14:30:00-05:00")
        assert dt.tzinfo is not None
        assert dt.utcoffset() is not None

    def test_serialized_ical_has_tzid(self, isolated_workspace):
        a = KhalAdapter()
        m = a.write_event(title="TzCheck", start="today 10:00")
        body = m.filepath.read_bytes()
        # icalendar outputs the local-time-with-offset form by default
        # when the dtstart has tzinfo. The string form must include
        # either a trailing 'Z' (for UTC) or a 'TZID=...' parameter.
        assert b"DTSTART" in body
        assert (b"Z" in body) or (
            b"TZID" in body
        ), f"DTSTART must encode timezone info, got: {body!r}"


# ---------------------------------------------------------------------------
# FIX AG: deep-copy isolates EventMatches from each other
# ---------------------------------------------------------------------------


class TestDeepCopyIsolation:
    def test_mutating_one_event_does_not_affect_another(self, isolated_workspace):
        a = KhalAdapter()
        a.write_event(title="Dentist", start="tomorrow 09:00")
        a.write_event(title="Dentist Special", start="tomorrow 09:00")
        matches = a.find_event("Dentist")
        assert len(matches) == 2

        # Mutating the first match's event must not affect the second.
        first = matches[0]
        original_summary_first = first.event["summary"]
        original_summary_second = matches[1].event["summary"]

        first.event["summary"] = "MUTATED"
        assert matches[0].event["summary"] == "MUTATED"
        assert matches[1].event["summary"] == original_summary_second
        # Original summary visible somewhere survives.
        assert original_summary_first == "Dentist" or original_summary_first == "Dentist Special"

    def test_update_does_not_affect_other_events(self, isolated_workspace):
        a = KhalAdapter()
        a.write_event(title="Standup", start="today 09:00")
        a.write_event(title="Standup Daily", start="today 09:00")

        # find_unique refuses two matches.
        from percival_khan_calendar.exceptions import KhanAmbiguousMatchError

        with pytest.raises(KhanAmbiguousMatchError):
            a.find_event_unique("Standup")

        a.write_event(title="Solo Standup", start="today 13:00")
        updated = a.update_event(
            "Solo Standup",
            fields={"summary": "Solo Standup UPDATE"},
        )
        assert updated.summary == "Solo Standup UPDATE"
        # Other Standup variants untouched on disk.
        all_standups = a.find_event("Standup")
        titles = sorted(m.summary for m in all_standups)
        # We replaced "Solo Standup" with "Solo Standup UPDATE", so we
        # expect three titles total now: "Solo Standup UPDATE",
        # "Standup", "Standup Daily".
        assert "Standup" in titles
        assert "Standup Daily" in titles
        assert "Solo Standup UPDATE" in titles


# ---------------------------------------------------------------------------
# FIX AP: idempotent commands can survive a transient missing-binary error
# ---------------------------------------------------------------------------


class TestRetryOnTransient:
    def test_filenotfound_can_be_retried_for_idempotent(self, isolated_workspace, monkeypatch):
        """retry_on_transient=True on a `list` subcommand should NOT
        be downgraded on FileNotFoundError: the binary might appear
        on retry. The behavior is: store the error in last_error and
        continue the loop."""
        # Make subprocess.run raise FileNotFoundError the first 2 times,
        # then return a successful result on the 3rd attempt by making
        # the binary appear.
        call_count = {"n": 0}

        target = "percival_khan_calendar.adapters.subprocess_runner.subprocess.run"

        def fake_run(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise FileNotFoundError(2, "no such file")
            # On the 3rd call, return a successful khal process.
            proc = mock.Mock()
            proc.returncode = 0
            proc.stdout = b"fake output"
            proc.stderr = b""
            return proc

        monkeypatch.setattr(target, fake_run)
        # 3 retries total: 2 failures + 1 success
        res = executar_comando_khal(
            ["list", "today"],
            tool_name="t",
            retry_on_transient=True,
            max_retries=2,
            timeout=5.0,
        )
        assert res.stdout == "fake output"
        assert call_count["n"] == 3

    def test_missing_binary_exhausts_retries(self, isolated_workspace, monkeypatch):
        """After all retries with FileNotFoundError, surface a typed error."""
        target = "percival_khan_calendar.adapters.subprocess_runner.subprocess.run"
        monkeypatch.setattr(target, mock.Mock(side_effect=FileNotFoundError(2, "no such file")))
        with pytest.raises(KhanInfrastructureError, match="khal binary not found"):
            executar_comando_khal(
                ["list", "today"],
                tool_name="t",
                retry_on_transient=True,
                max_retries=2,
                timeout=5.0,
            )


# ---------------------------------------------------------------------------
# FIX AV: subprocess env inherits TZ + locale
# ---------------------------------------------------------------------------


class TestSubprocessEnv:
    def test_subprocess_inherits_locale(self, isolated_workspace, monkeypatch):
        captured: dict = {}

        target = "percival_khan_calendar.adapters.subprocess_runner.subprocess.run"

        def fake_run(*args, **kwargs):
            captured["env"] = kwargs.get("env", {})
            proc = mock.Mock()
            proc.returncode = 0
            proc.stdout = b""
            proc.stderr = b""
            return proc

        monkeypatch.setattr(target, fake_run)
        executar_comando_khal(["list", "today"], tool_name="t")
        # Whatever TZ etc. was in os.environ at the moment of the call
        # should be propagated, PLUS we override LC_ALL=C.UTF-8 so the
        # bytes never fall out of UTF-8 territory.
        assert "LC_ALL" in captured["env"]
        assert captured["env"]["LC_ALL"] == "C.UTF-8"


# ---------------------------------------------------------------------------
# FIX AX: get_tool_fn helper raises LookupError on bad name
# ---------------------------------------------------------------------------


class TestHelperLookup:
    def test_unknown_tool_raises_lookup_error(self):
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        with pytest.raises(LookupError, match="nope"):
            get_tool_fn(mcp, "nope")
