"""Tests for khan_get_status, khan_list_calendars, khan_export_ics tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from percival_khan_calendar.adapters.subprocess_runner import (
    KhalResult,
)

from ._helpers import get_tool_fn


@pytest.fixture
def status_app(isolated_workspace):
    from fastmcp import FastMCP

    from percival_khan_calendar.tools.status import register_status_tools

    mcp = FastMCP("test")
    register_status_tools(mcp)
    return mcp


def test_health_check_returns_status(status_app, isolated_workspace):
    fn = get_tool_fn(status_app, "khan_get_status")
    out = fn()
    assert "operational" in out
    assert "Workspace:" in out
    assert "Lock:" in out


def test_list_calendars_happy(
    status_app, monkeypatch, isolated_workspace
):
    monkeypatch.setattr(
        "percival_khan_calendar.adapters.subprocess_runner.subprocess.run",
        lambda *a, **kw: KhalResult(
            stdout="nanobot", returncode=0, elapsed_ms=1
        ),
    )
    fn = get_tool_fn(status_app, "khan_list_calendars")
    out = fn()
    assert "nanobot" in out


def test_list_calendars_infra_error(
    status_app, monkeypatch, isolated_workspace
):
    from percival_khan_calendar.exceptions import KhanInfrastructureError

    def boom(*a, **kw):
        raise KhanInfrastructureError("khal binary not found")

    monkeypatch.setattr(
        "percival_khan_calendar.tools.status.executar_comando_khal",
        boom,
    )
    fn = get_tool_fn(status_app, "khan_list_calendars")
    out = fn()
    assert "khal binary not found" in out


def test_export_ics_default_path(
    status_app, monkeypatch, isolated_workspace
):
    from percival_khan_calendar.adapters.khal_adapter import KhalAdapter

    a = KhalAdapter()
    a.write_event(title="E1", start="today 10:00")
    a.write_event(title="E2", start="today 11:00")

    fn = get_tool_fn(status_app, "khan_export_ics")
    out = fn()
    assert "Exported" in out
    target = isolated_workspace / "export.ics"
    assert target.exists()
    body = target.read_bytes()
    assert b"E1" in body and b"E2" in body


def test_export_ics_rejects_path_traversal(
    status_app, isolated_workspace
):
    fn = get_tool_fn(status_app, "khan_export_ics")
    out = fn(output_path="/etc/passwd")
    assert "Refused" in out
