"""Tests for the workspace lock."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from percival_khan_calendar import constants
from percival_khan_calendar.adapters.locks import workspace_lock
from percival_khan_calendar.exceptions import KhanLockError


def test_lock_no_op_when_disabled(isolated_workspace: Path):
    """With ENABLE_LOCK=false (the default in tests), acquire/release is free."""
    assert constants.ENABLE_LOCK is False
    with workspace_lock(blocking=False):
        # Should be able to acquire a second one immediately.
        with workspace_lock(blocking=False):
            pass


def test_lock_blocks_second_acquire_when_enabled(monkeypatch):
    monkeypatch.setattr(constants, "ENABLE_LOCK", True)
    # Bypass the workspace_dir setattr by relying on the real path.
    # Make sure a lockfile path is available.
    constants.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    with workspace_lock(blocking=False):
        with pytest.raises(KhanLockError):
            with workspace_lock(blocking=False):
                pass


def test_lock_releases_on_exit(monkeypatch):
    monkeypatch.setattr(constants, "ENABLE_LOCK", True)
    constants.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    with workspace_lock(blocking=False):
        pass
    # Now we should be able to acquire again.
    with workspace_lock(blocking=False):
        assert True


def test_lock_blocking_waits(monkeypatch):
    monkeypatch.setattr(constants, "ENABLE_LOCK", True)
    constants.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    released = threading.Event()

    def worker():
        with workspace_lock(blocking=False):
            time.sleep(0.2)
        released.set()

    t = threading.Thread(target=worker)
    t.start()
    # Wait until the worker has acquired the lock.
    time.sleep(0.05)

    start = time.monotonic()
    with workspace_lock(blocking=True, timeout_s=2.0):
        elapsed = time.monotonic() - start
        # We should have waited ~0.15s for the worker to release.
        assert elapsed >= 0.05
    t.join(timeout=2.0)
    assert released.is_set()
