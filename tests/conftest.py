"""Shared fixtures for the calendar MCP test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from percival_khan_calendar import constants


@pytest.fixture
def isolated_workspace(monkeypatch, tmp_path: Path) -> Path:
    """Run each test against a temporary workspace.

    Mutates module-level constants so subprocess invocations don't touch
    the real $HOME/.nanobot/workspace/khalCalendar. Locking is disabled
    to avoid issues in CI/sandbox environments.
    """
    ws = tmp_path / "khalCalendar"
    data = ws / "data"
    conf = ws / "khal.conf"
    db = ws / "khal.db"
    lock = ws / "calendar.lock"

    monkeypatch.setattr(constants, "WORKSPACE_DIR", ws)
    monkeypatch.setattr(constants, "DATA_DIR", data)
    monkeypatch.setattr(constants, "CONF_FILE", conf)
    monkeypatch.setattr(constants, "DB_FILE", db)
    monkeypatch.setattr(constants, "LOCK_FILE", lock)
    monkeypatch.setattr(constants, "ENABLE_LOCK", False)

    yield ws
