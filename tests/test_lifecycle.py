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


# ---------------------------------------------------------------------------
# Round-6 follow-up: S1 — auto-heal of drifted khal.conf
# ---------------------------------------------------------------------------


def test_setup_workspace_regenerates_stale_conf(isolated_workspace):
    """When the on-disk khal.conf differs from the rendered template,
    setup_workspace rewrites it (auto-heal for downstream drift)."""
    from percival_khan_calendar.lifecycle import (
        _khal_conf_is_stale,
        setup_workspace,
    )

    # Write a deliberately stale version (the round-5 buggy layout):
    # ``path = DATA_DIR`` instead of ``DATA_DIR/<calendar>``.
    conf = isolated_workspace / "khal.conf"
    bad_content = "[calendars]\n\n[[nanobot]]\npath = /tmp/x\ntype = calendar\n"
    conf.write_text(bad_content, encoding="utf-8")
    assert _khal_conf_is_stale() is True

    setup_workspace()
    assert _khal_conf_is_stale() is False
    # Auto-heal preserved the same content rendered when no drift exists.
    new_content = conf.read_text(encoding="utf-8")
    assert "path = /tmp/x" not in new_content


def test_setup_workspace_is_idempotent_after_heal(isolated_workspace):
    """After auto-heal, calling setup_workspace again must NOT keep
    rewriting on every invocation (avoids needless churn)."""
    from percival_khan_calendar import constants
    from percival_khan_calendar.lifecycle import setup_workspace

    conf = constants.CONF_FILE
    # Force a drift cycle first:
    conf.write_text(
        "[calendars]\n\n[[nanobot]]\npath = /tmp/stale\ntype = calendar\n",
        encoding="utf-8",
    )
    setup_workspace()
    rendered_now = conf.read_text(encoding="utf-8")
    # Second call: same content, no rewrite churn.
    mtime_first = conf.stat().st_mtime_ns
    setup_workspace()
    mtime_second = conf.stat().st_mtime_ns
    assert mtime_first == mtime_second
    assert conf.read_text(encoding="utf-8") == rendered_now


def test_khal_conf_crlf_normalized_in_stale_check(isolated_workspace):
    """``_khal_conf_is_stale()`` ignores CRLF/LF differences so users
    syncing the file across platforms don't get spurious regenerations."""
    from percival_khan_calendar.lifecycle import (
        _khal_conf_is_stale,
        _render_khal_conf,
    )

    conf = isolated_workspace / "khal.conf"
    rendered = _render_khal_conf()
    conf.write_bytes(rendered.replace("\n", "\r\n").encode("utf-8"))
    # CRLF should NOT count as drift.
    assert _khal_conf_is_stale() is False
