"""Tests for lifecycle.setup_workspace."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_setup_workspace_creates_dirs_and_conf(isolated_workspace: Path):
    from percival_khan_calendar.lifecycle import setup_workspace

    assert setup_workspace() is True
    assert isolated_workspace.exists()
    assert (isolated_workspace / "data").exists()
    conf = isolated_workspace / "khal.conf"
    assert conf.exists()
    content = conf.read_text()
    assert "[calendars]" in content
    assert "[[nanobot]]" in content
    assert "default_calendar = nanobot" in content
    assert "[locale]" in content


def test_setup_workspace_idempotent(isolated_workspace: Path):
    """Calling again does not error and does not overwrite conf."""
    from percival_khan_calendar.lifecycle import setup_workspace

    setup_workspace()  # create
    original = (isolated_workspace / "khal.conf").read_text()
    assert setup_workspace() is True
    assert (isolated_workspace / "khal.conf").read_text() == original


def test_setup_workspace_retries_then_raises(monkeypatch, tmp_path):
    """If mkdir always fails, we raise OSError with a useful message."""
    from percival_khan_calendar import constants
    from percival_khan_calendar.lifecycle import setup_workspace

    bad = tmp_path / "no-perm"
    monkeypatch.setattr(
        constants,
        "WORKSPACE_DIR",
        bad,
    )
    call_count = {"n": 0}

    real_mkdir = Path.mkdir

    def failing_mkdir(self, *args, **kwargs):
        if str(self).startswith(str(bad)) and not self.exists():
            call_count["n"] += 1
            raise OSError(f"simulated permission denied ({call_count['n']})")
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)
    with pytest.raises(OSError, match="simulated permission"):
        setup_workspace(max_attempts=3)
    assert call_count["n"] == 3
