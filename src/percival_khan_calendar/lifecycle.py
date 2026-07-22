"""Workspace bootstrap with retries instead of ``sys.exit``.

The previous implementation killed the process on bootstrap failure,
which is hostile to an agentic runtime: it loses context and cannot
recover. We now try N times, then ``raise OSError`` so the caller can
decide what to do.

Auto-heal (round-6 follow-up): the workspace's ``khal.conf`` was
previously only ever rewritten when absent. That meant a deploy that
changed the expected layout (e.g. round-5's vdir-path fix where the
expected ``path`` shifted from ``DATA_DIR`` to ``DATA_DIR/<cal>``)
silently left old workspaces with a stale ``khal.conf``. The
helper ``_khal_conf_is_stale()`` now compares the on-disk file
against the rendered template and triggers ``_write_khal_conf()`` if
they differ. This costs one extra file read + one extra file write on
*every* boot but keeps the agent from being silently broken.
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

from . import constants
from .constants import LOCALE

logger = logging.getLogger("percival-khan-calendar.lifecycle")


def setup_workspace(*, max_attempts: int = 3) -> bool:
    """Bootstrap the khal workspace, with bounded retries.

    We deliberately read constants via ``constants.WORKSPACE_DIR``
    (attribute access) rather than module-level imports so that tests
    can monkeypatch the ``constants`` module at runtime.

    Returns:
        True on success.

    Raises:
        OSError: After all attempts fail (caller decides what to do).
    """
    last_exc: OSError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            constants.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
            constants.DATA_DIR.mkdir(parents=True, exist_ok=True)
            if not constants.CONF_FILE.exists() or _khal_conf_is_stale():
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


def _khal_conf_is_stale() -> bool:
    """Return ``True`` when the on-disk ``khal.conf`` differs from the
    template we would render now.

    Round-6 auto-heal: catches workspace drift introduced by upstream
    template changes. We compare the *rendered* template against the
    on-disk content; whitespace differences force a regenerate (we
    always control the format so this is safe and idempotent).
    """
    conf: Path = constants.CONF_FILE
    try:
        on_disk = conf.read_text(encoding="utf-8")
    except OSError:
        return True
    rendered = _render_khal_conf()
    # Normalize line endings so CRLF / LF drift on Windows doesn't
    # trigger spurious regenerations.
    return on_disk.replace("\r\n", "\n") != rendered.replace("\r\n", "\n")


def _write_khal_conf() -> None:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        prefix="khal.conf.",
        dir=str(constants.WORKSPACE_DIR),
    )
    try:
        tmp.write(_render_khal_conf())
        tmp.close()
        Path(tmp.name).replace(constants.CONF_FILE)
        logger.info("Wrote khal.conf to %s", constants.CONF_FILE)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise


def _render_khal_conf() -> str:
    # ``KhalAdapter`` writes each event under
    # ``DATA_DIR/<calendar_name>/<uid>.ics`` (see adapters/khal_adapter.py
    # ``_persist_event``). The vdir path declared here MUST match that
    # exact subdirectory — khal's vdir reader (``os.listdir``,
    # non-recursive) only sees ``.ics`` files placed directly inside
    # ``path``. Pointing ``path`` at ``DATA_DIR`` itself (one level too
    # high) silently hides every event from
    # ``khal list``/``agenda``/``calendar``/``printcalendars`` even
    # though the adapter's own (recursive) reads still find them.
    calendar_name = constants.DEFAULT_CALENDAR
    calendar_path = constants.DATA_DIR / calendar_name
    return (
        "[calendars]\n"
        "\n"
        f"[[{calendar_name}]]\n"
        f"path = {calendar_path}\n"
        "type = calendar\n"
        "\n"
        "[default]\n"
        f"default_calendar = {calendar_name}\n"
        "\n"
        "[locale]\n"
        f"timeformat = {LOCALE['timeformat']}\n"
        f"dateformat = {LOCALE['dateformat']}\n"
        f"longdateformat = {LOCALE['longdateformat']}\n"
        f"datetimeformat = {LOCALE['datetimeformat']}\n"
        f"longdatetimeformat = {LOCALE['longdatetimeformat']}\n"
        "\n"
        "[sqlite]\n"
        f"path = {constants.WORKSPACE_DIR}/khal.db\n"
    )


__all__ = ["setup_workspace", "_khal_conf_is_stale"]
