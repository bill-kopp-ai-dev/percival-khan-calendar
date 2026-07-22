"""Tests for khan_update_event tool."""

from __future__ import annotations

import pytest

from percival_khan_calendar.adapters.khal_adapter import EventMatch
from ._helpers import get_tool_fn


@pytest.fixture
def update_app(isolated_workspace):
    from fastmcp import FastMCP

    from percival_khan_calendar.adapters.khal_adapter import KhalAdapter
    from percival_khan_calendar.tools.update_event import (
        register_update_event_tools,
    )

    mcp = FastMCP("test")
    register_update_event_tools(mcp, KhalAdapter())
    return mcp


def test_update_event_happy(update_app, monkeypatch):
    captured: dict = {}

    def fake_update(self, old_term, *, fields):
        captured["old_term"] = old_term
        captured["fields"] = fields
        return EventMatch(
            filepath=None,
            ical=None,
            event=None,
            uid="uid-2",
            summary="Renamed",
            description="",
        )

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.khal_adapter.KhalAdapter.update_event",
        fake_update,
    )
    fn = get_tool_fn(update_app, "khan_update_event")
    out = fn(
        old_term="Original",
        new_title="Renamed",
        new_start="today 10:00",
    )
    assert "uid-2" in out
    assert "Renamed" in out
    assert captured["old_term"] == "Original"
    assert captured["fields"]["summary"] == "Renamed"


def test_update_event_not_found_message(update_app, monkeypatch):
    from percival_khan_calendar.exceptions import KhanNotFoundError

    def fake_update(self, old_term, *, fields):
        raise KhanNotFoundError("No event matches 'x'.")

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.khal_adapter.KhalAdapter.update_event",
        fake_update,
    )
    fn = get_tool_fn(update_app, "khan_update_event")
    out = fn(
        old_term="x",
        new_title="y",
        new_start="today",
    )
    assert "No event matches" in out
