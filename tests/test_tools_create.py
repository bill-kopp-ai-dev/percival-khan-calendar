"""Tests for khan_create_event tool."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from percival_khan_calendar.adapters.khal_adapter import EventMatch

from ._helpers import get_tool_fn


@pytest.fixture
def create_app(isolated_workspace):
    from fastmcp import FastMCP

    from percival_khan_calendar.adapters.khal_adapter import KhalAdapter
    from percival_khan_calendar.tools.create_event import (
        register_create_event_tools,
    )

    mcp = FastMCP("test")
    register_create_event_tools(mcp, KhalAdapter())
    return mcp


def test_create_event_happy(create_app, monkeypatch, isolated_workspace):
    def fake_write(self, **kwargs):
        return EventMatch(
            filepath=Path("/tmp/x.ics"),
            ical=None,
            event=None,
            uid="uid-1",
            summary=kwargs["title"],
            description="",
        )

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.khal_adapter.KhalAdapter.write_event",
        fake_write,
    )
    fn = get_tool_fn(create_app, "khan_create_event")
    out = fn(title="Standup", start="today 10:00")
    assert "uid-1" in out
    assert "Standup" in out


def test_create_event_tool_accepts_duration_and_persists_it(create_app, isolated_workspace):
    from icalendar import Calendar

    fn = get_tool_fn(create_app, "khan_create_event")
    out = fn(title="Duration through tool", start="2026-11-15T10:00:00Z", end="30m")

    assert "Created event" in out
    files = list((isolated_workspace / "data").rglob("*.ics"))
    assert len(files) == 1
    event = Calendar.from_ical(files[0].read_bytes()).walk("VEVENT")[0]
    assert event["DTEND"].dt - event["DTSTART"].dt == timedelta(minutes=30)


def test_create_event_propagates_error(create_app, monkeypatch):
    from percival_khan_calendar.exceptions import KhanError

    def fake_write(self, **kwargs):
        raise KhanError("nope")

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.khal_adapter.KhalAdapter.write_event",
        fake_write,
    )
    fn = get_tool_fn(create_app, "khan_create_event")
    out = fn(title="Standup", start="today 10:00")
    assert "nope" in out


def test_create_event_rejects_injection_at_model_level():
    from pydantic import ValidationError

    from percival_khan_calendar.models import CreateEventInput

    with pytest.raises(ValidationError):
        CreateEventInput(title="--evil", start="today")
