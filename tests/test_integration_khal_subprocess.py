"""Integration tests that exercise the real ``khal`` CLI subprocess.

Round-6 follow-up to issues/2026-07-22-percival-khan-calendar-list-events-mismatch:

The unit test suite mocks ``subprocess.run`` and exercises only the
adapter's recursive read path. As a result, the entire ``khal list`` /
``khal agenda`` / ``khal calendar`` family — which depends on a non-
recursive vdir reader inside the khal binary — was silently broken if
the on-disk ``khal.conf`` had ``path`` pointing at the wrong directory.
This file tests the *integration* surface: write an event through the
adapter, then assert that a real ``khal list`` invocation returns it.

These tests are opt-in via the ``integration`` marker so they don't run
in the default CI suite (they need a working ``khal`` binary in PATH
and a writable workspace). Run with ``pytest -m integration``.

The auto-heal in :func:`lifecycle.setup_workspace` keeps the conf
aligned with the adapter's layout, so if the integration test ever
flips to "negative", the suspect is the binary path / permissions,
not a stale ``khal.conf``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from percival_khan_calendar import constants
from percival_khan_calendar.adapters.khal_adapter import KhalAdapter
from percival_khan_calendar.adapters.subprocess_runner import (
    executar_comando_khal,
)
from percival_khan_calendar.lifecycle import setup_workspace

pytestmark = pytest.mark.integration


def _khal_available() -> bool:
    """Skip the entire module if khal isn't installed."""
    if shutil.which("khal") is not None:
        return True
    # Try locating inside the nearest ``.venv`` directory. Round-6
    # test helper: pytest-run via uv launches a Python whose
    # ``sys.executable`` lives in a .venv but its PATH lacks the
    # .venv/bin folder, so shutil.which misses the binary.
    here = Path(__file__).resolve().parent
    for ancestor in (here, *here.parents):
        candidate = ancestor / ".venv" / "bin" / "khal"
        if candidate.exists():
            return True
    return False


pytestmark = pytest.mark.skipif(
    not _khal_available(),
    reason="requires the `khal` binary in PATH",
)


class TestKhalSubprocessRoundTrip:
    """Round-6: tests invoke the real ``khal`` CLI subprocess via
    ``executar_comando_khal`` to detect layout drift between the
    adapter's recursive read path and khal's non-recursive vdir
    reader — exactly the bug described in the issue.

    These are skipped if the khal binary cannot be located.
    """

    def test_adapter_write_then_khal_list_sees_it(self, isolated_workspace):
        # The auto-heal flag in setup_workspace makes sure khal.conf
        # matches the rendered template regardless of any drift from
        # prior runs.
        from percival_khan_calendar.lifecycle import _khal_conf_is_stale

        setup_workspace()
        assert _khal_conf_is_stale() is False, (
            "Auto-heal failed: khal.conf still differs from the "
            "rendered template after setup_workspace()."
        )
        assert constants.CONF_FILE.exists()

        adapter = KhalAdapter()
        match = adapter.write_event(
            title="Integration Smoketest",
            start="tomorrow 10:00",
            end="tomorrow 11:00",
        )
        assert match.filepath.exists()

        # Now ask khal to list. The khal CLI is non-recursive
        # (``vdir`` / ``os.listdir``) — so this returns nothing if the
        # conf's ``path`` is one level above the adapter's writes.
        result = executar_comando_khal(
            ["list", "tomorrow", "1d"],
            tool_name="integration.khal_list",
            timeout=10.0,
        )
        assert "Integration Smoketest" in result.stdout, (
            f"khal CLI did not find the event the adapter wrote. "
            f"stdout was: {result.stdout!r}. "
            f"This means the on-disk khal.conf points one level "
            f"above the adapter's write location "
            f"(see khan_adapter._persist_event vs lifecycle._render_khal_conf)."
        )

    def test_layout_parity_after_bootstrap(self, tmp_path, monkeypatch):
        """Asserts the round-5 invariant: ``khal.conf`` path matches
        the directory the adapter writes into.

        If they diverge the production bug returns. The test setups a
        fresh isolated workspace via ``setup_workspace`` so the
        invariant must hold out-of-the-box; any test that runs after
        layout drift will fail loudly here instead of appearing as a
        missing-event issue downstream.
        """
        ws = tmp_path / "khalCalendar"
        monkeypatch.setattr(constants, "WORKSPACE_DIR", ws)
        monkeypatch.setattr(constants, "DATA_DIR", ws / "data")
        monkeypatch.setattr(constants, "CONF_FILE", ws / "khal.conf")
        monkeypatch.setattr(constants, "DB_FILE", ws / "khal.db")
        monkeypatch.setattr(constants, "LOCK_FILE", ws / "calendar.lock")
        monkeypatch.setattr(constants, "ENABLE_LOCK", False)
        setup_workspace()
        conf_text = constants.CONF_FILE.read_text(encoding="utf-8")
        expected = constants.DATA_DIR / constants.DEFAULT_CALENDAR
        assert f"path = {expected}" in conf_text, (
            f"khal.conf path is wrong. Layout:\n{conf_text!r}\nExpected: path = {expected}"
        )

        adapter = KhalAdapter()
        match = adapter.write_event(title="Layout Parity", start="tomorrow 11:00")
        assert match.filepath.parent == expected
