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


def test_list_events_calls_subprocess(tool_app, monkeypatch, isolated_workspace):
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
    # cmd[0] is the absolute path to the khal binary (round-6 fix
    # so subprocesses always find khal even when PATH differs from
    # the interpreter's). We assert the basename still ends in
    # "khal" so the test remains informative.
    assert captured["cmd"][0].endswith("khal")
    assert "list" in captured["cmd"]
    assert "today" in captured["cmd"]


def test_list_events_with_range(tool_app, monkeypatch, isolated_workspace):
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


def test_list_events_handles_empty(tool_app, monkeypatch, isolated_workspace):
    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        lambda *a, **kw: KhalResult(stdout="", returncode=0, elapsed_ms=1),
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    out = fn()
    assert "No events" in out


def test_list_events_infrastructure_error(tool_app, monkeypatch, isolated_workspace):
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
    """Argument-injection shield rejects '--foo'.

    The tool catches the Pydantic ValidationError and returns an error
    string instead of raising — this is the documented behavior since
    the validation layer refactor.
    """
    fn = get_tool_fn(tool_app[0], "khan_search_events")
    out = fn(query="--evil")
    assert "rejected the input" in out
    assert "recoverable_by_agent" in out


# -------------------- round-8: ISO date normalization ------------------
# Issue 2026-08-06-khan-list-events-date-parsing. khal 0.14.0 with
# ``dateformat = %d/%m/%Y`` rejects ISO dates (``2026-08-06``) with
# ``critical: Could not parse``. The tool now normalizes ISO → BR
# before invoking khal, so callers can pass either form.


def test_list_events_iso_start_date_normalized_to_br(tool_app, monkeypatch, isolated_workspace):
    """ISO ``2026-08-06`` start_date must reach khal as BR ``06/08/2026``.

    Regression for the original probe call:
    ``khan_list_events(start_date="2026-08-06", range_or_end="2d")``
    which used to exit 1 with ``critical: Could not parse``.
    """
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return KhalResult(stdout="", returncode=0, elapsed_ms=1)

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        fake_run,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    fn(start_date="2026-08-06", range_or_end="2d")
    # Subprocess cmd is [<khal-bin>, "-c", <conf>, "list", <start>, <range>]
    assert captured["cmd"][-2] == "06/08/2026"
    assert captured["cmd"][-1] == "2d"


def test_list_events_iso_range_or_end_normalized_to_br(tool_app, monkeypatch, isolated_workspace):
    """ISO in ``range_or_end`` is also normalized; relative durations pass through."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return KhalResult(stdout="", returncode=0, elapsed_ms=1)

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        fake_run,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    fn(start_date="2026-08-06", range_or_end="2026-08-08")
    assert captured["cmd"][-2] == "06/08/2026"
    assert captured["cmd"][-1] == "08/08/2026"


def test_list_events_br_literal_passes_through_unchanged(tool_app, monkeypatch, isolated_workspace):
    """BR literals are passed through unchanged (idempotent)."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return KhalResult(stdout="", returncode=0, elapsed_ms=1)

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        fake_run,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    fn(start_date="06/08/2026", range_or_end="08/08/2026")
    assert captured["cmd"][-2] == "06/08/2026"
    assert captured["cmd"][-1] == "08/08/2026"


def test_list_events_relative_term_passes_through(tool_app, monkeypatch, isolated_workspace):
    """Relative terms (``today``) and durations (``7d``) are untouched."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return KhalResult(stdout="", returncode=0, elapsed_ms=1)

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        fake_run,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    fn(start_date="today", range_or_end="7d")
    assert captured["cmd"][-2] == "today"
    assert captured["cmd"][-1] == "7d"


def test_list_events_mixed_iso_start_br_end(tool_app, monkeypatch, isolated_workspace):
    """ISO start + BR end is normalized in place; khal sees both as BR."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return KhalResult(stdout="", returncode=0, elapsed_ms=1)

    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        fake_run,
    )
    fn = get_tool_fn(tool_app[0], "khan_list_events")
    fn(start_date="2026-08-06", range_or_end="08/08/2026")
    assert captured["cmd"][-2] == "06/08/2026"
    assert captured["cmd"][-1] == "08/08/2026"
