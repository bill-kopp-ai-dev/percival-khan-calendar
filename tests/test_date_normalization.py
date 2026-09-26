"""Unit tests for the ISO→BR date normalizer (round-8 fix).

Issue: ``agent-docker/mcp_servers/MCP_Docs/Issues/
2026-08-06-khan-list-events-date-parsing.md``.

These tests pin the public contract of ``normalize_date_to_br``:
- ISO ``YYYY-MM-DD`` is rewritten to ``DD/MM/YYYY``.
- ISO datetimes ``YYYY-MM-DDThh:mm:ss`` are rewritten to
  ``DD/MM/YYYY`` (the time component is dropped — list/search take a
  date, not a timestamp).
- BR literals, relative terms, durations, and malformed strings pass
  through untouched.
- Empty string is passed through (caller may substitute a default).
"""

from __future__ import annotations

import pytest

from percival_khan_calendar.date_normalization import (
    _ISO_DATE_RE,
    normalize_date_to_br,
)


class TestIsoToBr:
    """ISO dates get rewritten to BR (DD/MM/YYYY)."""

    def test_iso_date_simple(self) -> None:
        assert normalize_date_to_br("2026-08-06") == "06/08/2026"

    def test_iso_date_end_of_year(self) -> None:
        assert normalize_date_to_br("2025-12-31") == "31/12/2025"

    def test_iso_date_leading_zeros(self) -> None:
        assert normalize_date_to_br("2026-01-02") == "02/01/2026"

    def test_iso_datetime_drops_time(self) -> None:
        """ISO datetime ``YYYY-MM-DDThh:mm:ss`` becomes BR with time dropped.

        khal list/agenda take a date, not a timestamp; passing the time
        component would confuse ``khal list 06/08/2026T14:30:00`` and
        trigger another ``Could not parse``. The caller decides whether
        to add a separate time field downstream.
        """
        assert normalize_date_to_br("2026-08-06T14:30:00") == "06/08/2026"

    def test_iso_datetime_with_tz_drops_time_and_tz(self) -> None:
        assert normalize_date_to_br("2026-08-06T14:30:00+02:00") == "06/08/2026"

    def test_iso_datetime_microseconds_drops_time(self) -> None:
        assert normalize_date_to_br("2026-08-06T14:30:00.123456") == "06/08/2026"


class TestPassThrough:
    """Anything that isn't a clean ISO date is returned untouched."""

    def test_br_literal_passes_through(self) -> None:
        """Already-BR input is returned unchanged (idempotent)."""
        assert normalize_date_to_br("06/08/2026") == "06/08/2026"

    def test_br_literal_single_digit_day(self) -> None:
        assert normalize_date_to_br("6/8/2026") == "6/8/2026"

    def test_relative_term_today(self) -> None:
        assert normalize_date_to_br("today") == "today"

    def test_relative_term_tomorrow(self) -> None:
        assert normalize_date_to_br("tomorrow") == "tomorrow"

    def test_relative_term_now(self) -> None:
        assert normalize_date_to_br("now") == "now"

    def test_duration_days(self) -> None:
        assert normalize_date_to_br("7d") == "7d"

    def test_duration_weeks(self) -> None:
        assert normalize_date_to_br("1w") == "1w"

    def test_duration_months(self) -> None:
        assert normalize_date_to_br("30d") == "30d"

    def test_empty_string_passes_through(self) -> None:
        """Empty stays empty — caller decides whether to default."""
        assert normalize_date_to_br("") == ""


class TestMalformedIso:
    """ISO-shaped but invalid strings pass through to khal for native errors."""

    def test_iso_with_slashes_passes_through(self) -> None:
        """``2026/08/06`` is not the canonical ``YYYY-MM-DD`` shape; leave alone."""
        assert normalize_date_to_br("2026/08/06") == "2026/08/06"

    def test_iso_single_digit_month_passes_through(self) -> None:
        """``2026-8-6`` doesn't match the strict ``\\d{2}`` month/day."""
        assert normalize_date_to_br("2026-8-6") == "2026-8-6"

    def test_garbage_passes_through(self) -> None:
        assert normalize_date_to_br("not-a-date") == "not-a-date"


class TestRegexAnchor:
    """Pin the regex so a future change can't widen the ISO pattern by accident."""

    @pytest.mark.parametrize(
        "value",
        [
            "2026-08-06",
            "2026-08-06T14:30:00",
            "2026-08-06T14:30:00.123456",
            "2026-08-06T14:30:00+02:00",
        ],
    )
    def test_iso_shape_matches(self, value: str) -> None:
        assert _ISO_DATE_RE.match(value) is not None

    @pytest.mark.parametrize(
        "value",
        [
            "06/08/2026",
            "today",
            "7d",
            "2026/08/06",
            "2026-8-6",
            "-2026-08-06",  # starts with dash (rejected by injection shield upstream)
        ],
    )
    def test_non_iso_does_not_match(self, value: str) -> None:
        assert _ISO_DATE_RE.match(value) is None
