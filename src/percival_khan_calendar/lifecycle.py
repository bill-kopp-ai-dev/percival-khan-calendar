"""Workspace bootstrap with retries instead of ``sys.exit``.

The previous implementation killed the process on bootstrap failure,
which is hostile to an agentic runtime: it loses context and cannot
recover. We now try N times, then ``raise OSError`` so the caller can
decide what to do (the FastMCP entrypoint logs and exits with a clear
message, but at least gives the logs a chance).
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

from .constants import CONF_FILE, DATA_DIR, LOCALE, WORKSPACE_DIR

logger = logging.getLogger("percival-khan-calendar.lifecycle")


def setup_workspace(*, max_attempts: int = 3) -> bool:
    """Bootstrap the khal workspace, with bounded retries.

    Returns:
        True on success.

    Raises:
        OSError: After all attempts fail (caller decides what to do).
    """
    last_exc: OSError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if not CONF_FILE.exists():
                _write_khal_conf()
            return True
        except OSError as exc:
            last_exc = exc
            logger.warning(
                "setup_workspace attempt %d/%d failed: %s",
                attempt,
                max_attempts,
                exc,
            )
            time.sleep(0.5 * attempt)

    assert last_exc is not None
    raise last_exc


def _write_khal_conf() -> None:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        prefix="khal.conf.",
        dir=str(WORKSPACE_DIR),
    )
    try:
        tmp.write(_render_khal_conf())
        tmp.close()
        Path(tmp.name).replace(CONF_FILE)
        logger.info("Wrote khal.conf to %s", CONF_FILE)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise


def _render_khal_conf() -> str:
    return (
        "[calendars]\n"
        "\n"
        "[[nanobot]]\n"
        f"path = {DATA_DIR}\n"
        "type = calendar\n"
        "\n"
        "[default]\n"
        "default_calendar = nanobot\n"
        "\n"
        "[locale]\n"
        f"timeformat = {LOCALE['timeformat']}\n"
        f"dateformat = {LOCALE['dateformat']}\n"
        f"longdateformat = {LOCALE['longdateformat']}\n"
        f"datetimeformat = {LOCALE['datetimeformat']}\n"
        f"longdatetimeformat = {LOCALE['longdatetimeformat']}\n"
        "\n"
        "[sqlite]\n"
        f"path = {WORKSPACE_DIR}/khal.db\n"
    )


__all__ = ["setup_workspace"]
