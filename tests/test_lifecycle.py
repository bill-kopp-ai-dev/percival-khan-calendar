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


def test_khal_conf_calendar_path_matches_adapter_write_location(isolated_workspace: Path):
    """Regression: khal.conf's ``path`` must point at the exact directory
    KhalAdapter writes events into (DATA_DIR/<calendar_name>), not at
    DATA_DIR itself. khal's vdir reader is non-recursive (os.listdir),
    so one path level off silently hides every event from `khal list`/
    `agenda`/`calendar`/`printcalendars` even though the adapter's own
    (recursive) reads still find them."""
    from percival_khan_calendar import constants
    from percival_khan_calendar.adapters.khal_adapter import KhalAdapter

    conf = isolated_workspace / "khal.conf"
    content = conf.read_text()
    expected_path = constants.DATA_DIR / constants.DEFAULT_CALENDAR
    assert f"path = {expected_path}" in content

    adapter = KhalAdapter()
    match = adapter.write_event(title="Path Check", start="today 10:00")
    assert match.filepath.parent == expected_path


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
