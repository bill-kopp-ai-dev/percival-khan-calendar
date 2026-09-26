"""Date-input normalization for khal commands.

khal 0.14.0 only accepts dates that match the user's configured
``[locale] dateformat`` (default ``%d/%m/%Y``). When the user has
``dateformat = %d/%m/%Y`` (BR layout, the workspace's actual
configuration), ISO inputs (``2026-08-06``) are rejected with::

    critical: Could not parse "('2026-08-06', '2d')".

This module converts ISO-style absolute dates to BR-style before they
hit the khal subprocess, so callers (humans or agents) can pass either
format. Relative terms (``today``, ``tomorrow``, ``now``) and durations
(``7d``, ``1w``) are passed through untouched — they don't depend on
the configured dateformat.

Caveats:

- Only ISO dates with the canonical shape ``YYYY-MM-DD`` (optionally
  followed by ``T...`` time component) are converted. Anything else
  (BR literals, relative terms, durations, malformed strings) passes
  through unchanged so the user always sees khal's native error if
  their input is genuinely wrong.
- The function is intentionally idempotent: passing a value that's
  already BR (``06/08/2026``) returns it as-is.

Tests covering the supported shapes live in ``tests/test_date_normalization.py``.
"""

from __future__ import annotations

import re
from typing import Final

# Matches ``YYYY-MM-DD`` (optionally followed by ``T<time>`` for ISO
# datetimes). Anchored so a bare ``06/08/2026`` or ``today`` never matches.
# Examples that DO match:  ``2026-08-06``, ``2026-08-06T14:30:00``,
#                          ``2026-08-06T14:30:00+02:00``.
# Examples that do NOT match: ``06/08/2026``, ``today``, ``7d``, ``-1d``,
#                             ``2026/08/06``, ``2026-8-6``.
_ISO_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$")


def normalize_date_to_br(value: str) -> str:
    """Convert an ISO absolute date to BR (``DD/MM/YYYY``), pass through anything else.

    Args:
        value: User-supplied date/duration string. May be ``""``, ``"today"``,
            ``"06/08/2026"``, ``"2026-08-06"``, ``"2026-08-06T14:30:00"``,
            ``"7d"``, etc.

    Returns:
        ``value`` unchanged for non-ISO inputs; for ISO inputs,
        ``DD/MM/YYYY`` with the same year/month/day. Time component
        (if present) is dropped — list/search commands take a date,
        not a timestamp.

    Note:
        Empty strings pass through (caller may want to use the default
        ``"today"``). No exception is raised for malformed ISO — the
        caller still gets khal's native error and can decide what to do.
    """
    if not value:
        return value
    match = _ISO_DATE_RE.match(value)
    if not match:
        return value
    year, month, day = match.group(1), match.group(2), match.group(3)
    return f"{day}/{month}/{year}"


__all__ = ["normalize_date_to_br", "_ISO_DATE_RE"]
