"""Cross-process file locking for the calendar workspace.

We use POSIX advisory locks (``fcntl.flock``) on a single file anchor:

    ``<WORKSPACE_DIR>/calendar.lock``

The locks are advisory — a misbehaving process may bypass them, but the
common race between two MCP agents is now caught.

On platforms without ``fcntl`` (Windows), the lock is a no-op
(``ENABLE_LOCK`` switch controls it).
"""

from __future__ import annotations

import contextlib
import errno
import fcntl  # type: ignore[import-not-found]  # POSIX-only
import logging
import os
import time
from pathlib import Path
from typing import Iterator

from .. import constants
from ..exceptions import KhanLockError

logger = logging.getLogger("percival-khan-calendar.locks")


def _lockfile_path() -> Path:
    path = constants.LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    return path


@contextlib.contextmanager
def workspace_lock(
    *,
    blocking: bool = False,
    timeout_s: float = 5.0,
) -> Iterator[None]:
    """Acquire an exclusive lock on the calendar workspace.

    Args:
        blocking: If True, wait up to ``timeout_s``. If False (default),
            fail immediately if the lock is held.
        timeout_s: How long to wait when blocking=True.

    Raises:
        KhanLockError: When the lock cannot be acquired within the
            budget. ``ENABLE_LOCK=false`` short-circuits this to a no-op.
    """
    if not constants.ENABLE_LOCK:
        yield
        return

    path = _lockfile_path()
    fd = os.open(str(path), os.O_RDWR)
    try:
        op = fcntl.LOCK_EX
        if not blocking:
            op |= fcntl.LOCK_NB
            try:
                fcntl.flock(fd, op)
            except OSError as exc:
                if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise KhanLockError(
                        f"Workspace lock {path} held by another process"
                    ) from exc
                raise
        else:
            deadline = time.monotonic() + timeout_s
            while True:
                try:
                    fcntl.flock(fd, op)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                        raise
                    if time.monotonic() > deadline:
                        raise KhanLockError(
                            f"Workspace lock {path} not released "
                            f"within {timeout_s}s"
                        ) from exc
                time.sleep(0.05)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            logger.warning("Failed to release workspace lock", exc_info=True)
        os.close(fd)


__all__ = ["workspace_lock"]
