"""Tests for khan_delete_event and khan_delete_event_safe tools."""

from __future__ import annotations

import pytest

from percival_khan_calendar.adapters.khal_adapter import KhalAdapter

from ._helpers import get_tool_fn


@pytest.fixture
def delete_app(isolated_workspace):
    from fastmcp import FastMCP

    from percival_khan_calendar.tools.delete_event import (
        register_delete_event_tools,
    )

    mcp = FastMCP("test")
    adapter = KhalAdapter()
    register_delete_event_tools(mcp, adapter)
    return mcp, adapter


def test_delete_event_happy(delete_app):
    mcp, adapter = delete_app
    adapter.write_event(title="Disposable", start="today 10:00")
    fn = get_tool_fn(mcp, "khan_delete_event")
    out = fn(exact_term="Disposable")
    assert "Deleted" in out


def test_delete_event_not_found(delete_app):
    mcp, _ = delete_app
    fn = get_tool_fn(mcp, "khan_delete_event")
    out = fn(exact_term="nothing")
    assert "No event matches" in out


def test_delete_safe_dry_run(delete_app):
    mcp, adapter = delete_app
    adapter.write_event(title="TestMe", start="today 12:00")
    fn = get_tool_fn(mcp, "khan_delete_event_safe")
    out = fn(exact_term="TestMe")
    assert "Dry run" in out
    assert len(adapter.find_event("TestMe")) == 1


def test_delete_safe_confirm_removes(delete_app):
    mcp, adapter = delete_app
    adapter.write_event(title="TestMe", start="today 12:00")
    fn = get_tool_fn(mcp, "khan_delete_event_safe")
    out = fn(exact_term="TestMe", confirm=True)
    assert "Deleted" in out
    assert adapter.find_event("TestMe") == []


def test_delete_safe_many_matches_refuses(delete_app):
    mcp, adapter = delete_app
    adapter.write_event(title="Standup", start="today 09:00")
    adapter.write_event(title="Standup Daily", start="today 09:00")
    fn = get_tool_fn(mcp, "khan_delete_event_safe")
    out = fn(exact_term="Standup")
    assert "Refused" in out
    assert "candidates" in out.lower() or "Candidates" in out


def test_get_event_returns_match(delete_app):
    mcp, adapter = delete_app
    adapter.write_event(
        title="My Event", start="today 10:00", description="Note",
    )
    fn = get_tool_fn(mcp, "khan_get_event")
    out = fn(exact_term="My Event")
    assert "UID:" in out
    assert "Summary: My Event" in out


def test_get_event_not_found(delete_app):
    mcp, _ = delete_app
    fn = get_tool_fn(mcp, "khan_get_event")
    out = fn(exact_term="nothing")
    assert "No event matches" in out
