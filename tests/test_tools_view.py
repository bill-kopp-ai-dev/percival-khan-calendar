"""Tests for khan_view_agenda and khan_view_calendar tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from percival_khan_calendar.adapters.subprocess_runner import (
    KhalResult,
)

from ._helpers import get_tool_fn


@pytest.fixture
def view_app(isolated_workspace: Path):
    from fastmcp import FastMCP

    from percival_khan_calendar.tools.view import register_view_tools

    mcp = FastMCP("test")
    register_view_tools(mcp)
    return mcp


def test_view_agenda_happy(view_app, monkeypatch, isolated_workspace):
    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        lambda *a, **kw: KhalResult(stdout="10:00 Standup", returncode=0, elapsed_ms=1),
    )
    fn = get_tool_fn(view_app, "khan_view_agenda")
    out = fn(period="7d")
    assert "Standup" in out
    assert "Agenda" in out


def test_view_agenda_empty_returns_msg(view_app, monkeypatch, isolated_workspace):
    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        lambda *a, **kw: KhalResult(stdout="", returncode=0, elapsed_ms=1),
    )
    fn = get_tool_fn(view_app, "khan_view_agenda")
    out = fn()
    assert out == "No events."


def test_view_agenda_invalid_period_rejected():
    """Validation via Pydantic (tool layer test)."""
    from pydantic import ValidationError

    from percival_khan_calendar.models import ViewAgendaInput

    with pytest.raises(ValidationError):
        ViewAgendaInput(period="forever")


def test_view_calendar_happy(view_app, monkeypatch, isolated_workspace):
    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        lambda *a, **kw: KhalResult(stdout="Mo Tu We\n 1  2  3", returncode=0, elapsed_ms=1),
    )
    fn = get_tool_fn(view_app, "khan_view_calendar")
    out = fn(reference_month="today")
    assert "Monthly View" in out


def test_view_calendar_long_truncates(view_app, monkeypatch, isolated_workspace):
    big = "x" * 5000
    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        lambda *a, **kw: KhalResult(stdout=big, returncode=0, elapsed_ms=1),
    )
    fn = get_tool_fn(view_app, "khan_view_calendar")
    out = fn()
    assert "[Conteúdo truncado." in out
