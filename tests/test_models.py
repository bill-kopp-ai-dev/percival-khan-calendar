"""Unit tests for Pydantic input models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from percival_khan_calendar.models import (
    CreateEventInput,
    DeleteEventInput,
    ListEventsInput,
    SearchEventsInput,
    UpdateEventInput,
    ViewAgendaInput,
    ViewCalendarInput,
)


class TestCreateEventInput:
    def test_minimal_valid(self):
        m = CreateEventInput(title="Meeting", start="tomorrow 14:00")
        assert m.alarm == ""
        assert m.recurrence == ""

    def test_alarm_must_match_pattern(self):
        with pytest.raises(ValidationError):
            CreateEventInput(title="x", start="today", alarm="rm -rf /")

    def test_alarm_one_minute_ok(self):
        m = CreateEventInput(title="x", start="today", alarm="5m")
        assert m.alarm == "5m"

    def test_alarm_one_day_ok(self):
        m = CreateEventInput(title="x", start="today", alarm="2d")
        assert m.alarm == "2d"

    def test_alarm_invalid_unit_rejected(self):
        with pytest.raises(ValidationError):
            CreateEventInput(title="x", start="today", alarm="5x")

    def test_start_rejects_dash_prefix(self):
        with pytest.raises(ValidationError):
            CreateEventInput(title="x", start="--evil")

    def test_location_rejects_double_dash(self):
        with pytest.raises(ValidationError):
            CreateEventInput(title="x", start="today", location="foo -- bar")

    def test_recurrence_validates_against_set(self):
        with pytest.raises(ValidationError):
            CreateEventInput(title="x", start="today", recurrence="fortnightly")

    def test_recurrence_lowercased(self):
        m = CreateEventInput(title="x", start="today", recurrence="DAILY")
        assert m.recurrence == "daily"

    def test_title_required(self):
        with pytest.raises(ValidationError):
            CreateEventInput(title="", start="today")

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            CreateEventInput(title="x" * 201, start="today")

    def test_optional_fields_default(self):
        m = CreateEventInput(title="x", start="today")
        assert m.end == ""
        assert m.description == ""
        assert m.location == ""


class TestListAndSearch:
    def test_list_defaults(self):
        m = ListEventsInput()
        assert m.start_date == "today"
        assert m.range_or_end == ""

    def test_list_rejects_dash(self):
        with pytest.raises(ValidationError):
            ListEventsInput(start_date="--evil")
        with pytest.raises(ValidationError):
            ListEventsInput(range_or_end="-r foo")

    def test_search_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            SearchEventsInput(query="")

    def test_search_rejects_dash(self):
        with pytest.raises(ValidationError):
            SearchEventsInput(query="--foo")


class TestUpdateAndDelete:
    def test_update_minimal(self):
        m = UpdateEventInput(
            old_term="old",
            new_title="new",
            new_start="today 10:00",
        )
        assert m.new_end == ""
        assert m.new_description == ""

    def test_update_rejects_injection(self):
        with pytest.raises(ValidationError):
            UpdateEventInput(
                old_term="old",
                new_title="--evil",
                new_start="today",
            )

    def test_delete_rejects_injection(self):
        with pytest.raises(ValidationError):
            DeleteEventInput(exact_term="--evil")


class TestView:
    def test_view_agenda_default(self):
        assert ViewAgendaInput().period == "7d"

    def test_view_agenda_literal(self):
        m = ViewAgendaInput(period="30d")
        assert m.period == "30d"

    def test_view_agenda_invalid_literal(self):
        with pytest.raises(ValidationError):
            ViewAgendaInput(period="forever")

    def test_view_calendar_default(self):
        assert ViewCalendarInput().reference_month == "today"

    def test_view_calendar_too_long(self):
        with pytest.raises(ValidationError):
            ViewCalendarInput(reference_month="x" * 200)

    def test_view_calendar_rejects_argument_injection(self):
        """Regression: reference_month is forwarded as a raw positional
        arg to the `khal calendar` subprocess (view.py), so it needs the
        same anti-argument-injection guard every other free-text field
        has (e.g. a value like '--format' or '-a' could smuggle in a
        recognized khal flag)."""
        with pytest.raises(ValidationError):
            ViewCalendarInput(reference_month="--format=x")
        with pytest.raises(ValidationError):
            ViewCalendarInput(reference_month="-a")
