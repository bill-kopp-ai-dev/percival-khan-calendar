"""Central constants for the calendar MCP server.

All magic numbers and configuration strings live here. Keep this file
free of side effects beyond ``os.environ`` lookups at import time
(constants are computed once).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Workspace layout (overridable via env).
# ---------------------------------------------------------------------------

WORKSPACE_DIR: Final[Path] = Path(
    os.environ.get(
        "KHAN_WORKSPACE_DIR",
        str(Path.home() / ".nanobot" / "workspace" / "khalCalendar"),
    )
)
DATA_DIR: Final[Path] = WORKSPACE_DIR / "data"
CONF_FILE: Final[Path] = WORKSPACE_DIR / "khal.conf"
DB_FILE: Final[Path] = WORKSPACE_DIR / "khal.db"
LOCK_FILE: Final[Path] = WORKSPACE_DIR / "calendar.lock"

# ---------------------------------------------------------------------------
# Calendar identity (single source — Fase 7 may allow multiple).
# ---------------------------------------------------------------------------

DEFAULT_CALENDAR: Final[str] = os.environ.get("KHAN_DEFAULT_CALENDAR", "nanobot")

# ---------------------------------------------------------------------------
# Truncation constants.
# ---------------------------------------------------------------------------

MAX_DAILY_EVENTS: Final[int] = 200
MAX_AGENDA_CHARS: Final[int] = 4000  # Telegram limit (informational)
MAX_CONTEXT_CHARS: Final[int] = 4000  # LLM context safety

# Input length limits.
MAX_TITLE_LEN: Final[int] = 200
MAX_DESCRIPTION_LEN: Final[int] = 2000
MAX_LOCATION_LEN: Final[int] = 200
MAX_QUERY_LEN: Final[int] = 128
MAX_SHORT_STR_LEN: Final[int] = 64

# ---------------------------------------------------------------------------
# Subprocess defaults.
# ---------------------------------------------------------------------------

DEFAULT_SUBPROCESS_TIMEOUT: Final[float] = float(os.environ.get("KHAN_SUBPROCESS_TIMEOUT", "15"))
LOCK_TIMEOUT: Final[float] = 5.0

# ---------------------------------------------------------------------------
# Locale (default BR; can be overridden via env when generating khal.conf).
# ---------------------------------------------------------------------------

LOCALE: Final[dict[str, str]] = {
    "timeformat": os.environ.get("KHAN_TIMEFORMAT", "%H:%M"),
    "dateformat": os.environ.get("KHAN_DATEFORMAT", "%d/%m/%Y"),
    "longdateformat": os.environ.get("KHAN_LONGDATEFORMAT", "%d/%m/%Y"),
    "datetimeformat": os.environ.get("KHAN_DATETIMEFORMAT", "%d/%m/%Y %H:%M"),
    "longdatetimeformat": os.environ.get("KHAN_LONGDATETIMEFORMAT", "%d/%m/%Y %H:%M"),
}

# ---------------------------------------------------------------------------
# iCal / khal option constraints.
# ---------------------------------------------------------------------------

ALLOWED_ALARM_PATTERN: Final[str] = r"^\d+[smhd]$"
ALLOWED_RECURRENCE_VALUES: Final[frozenset[str]] = frozenset(
    {"daily", "weekly", "monthly", "yearly"}
)
ALLOWED_AGENDA_PERIODS: Final[frozenset[str]] = frozenset({"today", "tomorrow", "7d", "30d"})

# ---------------------------------------------------------------------------
# Locking (Fase 6).
# ---------------------------------------------------------------------------

ENABLE_LOCK: Final[bool] = os.environ.get("KHAN_ENABLE_LOCK", "true").lower() in (
    "1",
    "true",
    "yes",
)
