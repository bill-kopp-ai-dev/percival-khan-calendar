"""Tests for khan_list_events and khan_search_events tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from percival_khan_calendar.adapters.khal_adapter import KhalAdapter
from percival_khan_calendar.adapters.subprocess_runner import (
    KhalResult,
)
from percival_khan_calendar.exceptions import KhanInfrastructureError
from ._helpers import get_tool_fn


@pytest.fixture
def tool_app(isolated_workspace: Path):
    from fastmcp import FastMCP

    from percival_khan_calendar.tools.list_events import (
        register_list_events_tools,
    )

    mcp = FastMCP("test")
    adapter = KhalAdapter()
    register_list_events_tools(mcp, adapter)
    return mcp, adapter


def test_list_events_calls_subprocess(
    tool_app, monkeypatch, isolated_workspace
):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return KhalResult(stdout="event 1\nevent 2", returncode=0, elapsed_ms=1)

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        fake_run,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    out = fn(start_date="today")
    assert "event 1" in out
    assert captured["cmd"][0] == "khal"
    assert "list" in captured["cmd"]
    assert "today" in captured["cmd"]


def test_list_events_with_range(
    tool_app, monkeypatch, isolated_workspace
):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return KhalResult(stdout="x", returncode=0, elapsed_ms=1)

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        fake_run,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    fn(start_date="today", range_or_end="7d")
    assert "7d" in captured["cmd"]


def test_list_events_handles_empty(
    tool_app, monkeypatch, isolated_workspace
):
    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        lambda *a, **kw: KhalResult(stdout="", returncode=0, elapsed_ms=1),
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    out = fn()
    assert "No events" in out


def test_list_events_infrastructure_error(
    tool_app, monkeypatch, isolated_workspace
):
    def boom(cmd, **kwargs):
        raise KhanInfrastructureError("khal binary not found")

    monkeypatch.setattr(
        "percival_khan_calendar.tools.list_events.executar_comando_khal",
        boom,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    out = fn(start_date="today")
    assert "khal binary not found" in out
    assert "recoverable" in out


def test_search_events_with_matches(tool_app, isolated_workspace):
    _, adapter = tool_app
    adapter.write_event(title="Dentist", start="tomorrow 09:00")
    adapter.write_event(title="Dentist Special", start="tomorrow 09:00")
    fn = get_tool_fn(tool_app[0], "khan_search_events")
    out = fn(query="Dentist")
    assert "Dentist" in out
    assert "Dentist Special" in out


def test_search_events_no_matches(tool_app, isolated_workspace):
    fn = get_tool_fn(tool_app[0], "khan_search_events")
    out = fn(query="nothing")
    assert "No events match" in out


def test_search_events_rejects_dash(tool_app, isolated_workspace):
    """Argument-injection shield rejects '--foo'."""
    fn = get_tool_fn(tool_app[0], "khan_search_events")
    with pytest.raises(Exception):
        fn(query="--evil")
