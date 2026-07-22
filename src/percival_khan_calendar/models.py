"""Pydantic input models for the calendar MCP tools.

These models perform the first line of defence: invalid inputs never reach
the khal subprocess. Tools that mutate the calendar additionally go
through ``StoredEvent`` validation when reading from disk.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .constants import (
    ALLOWED_ALARM_PATTERN,
    ALLOWED_RECURRENCE_VALUES,
    MAX_DESCRIPTION_LEN,
    MAX_LOCATION_LEN,
    MAX_QUERY_LEN,
    MAX_SHORT_STR_LEN,
    MAX_TITLE_LEN,
)

# Strip ASCII control characters (0x00-0x1F, except whitespace tab/nl,
# and DEL) from string inputs to defeat shell/control injection via
# payload bytes that Pydantic's plain ``str`` would not otherwise filter.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_free_text(v: str) -> str:
    """Strip control characters and normalize unicode.

    Returns the cleaned string. Empty string after stripping is
    considered valid; Pydantic field length constraints already
    enforce min/max.
    """
    if not isinstance(v, str):
        v = str(v)
    cleaned = _CONTROL_CHARS_RE.sub("", v)
    cleaned = unicodedata.normalize("NFC", cleaned)
    return cleaned


class ListEventsInput(BaseModel):
    """Validate inputs for ``khan_list_events``."""

    start_date: str = Field(
        default="today",
        description=(
            "Starting point for the list. Accepts 'today', 'tomorrow', 'now', or DD/MM/YYYY."
        ),
        max_length=MAX_SHORT_STR_LEN,
    )
    range_or_end: str = Field(
        default="",
        description="Duration like '7d' or end date DD/MM/YYYY.",
        max_length=MAX_SHORT_STR_LEN,
    )

    @field_validator("start_date", "range_or_end")
    @classmethod
    def _no_injection(cls, v: str) -> str:
        v = _sanitize_free_text(v)
        if v.startswith("-") or "--" in v:
            raise ValueError(
                "Inputs starting with '-' or containing '--' are rejected "
                "(argument-injection shield)."
            )
        return v


class SearchEventsInput(BaseModel):
    """Validate inputs for ``khan_search_events``."""

    query: str = Field(
        min_length=1,
        max_length=MAX_QUERY_LEN,
        description="Keyword or phrase to search for.",
    )

    @field_validator("query")
    @classmethod
    def _no_injection(cls, v: str) -> str:
        v = _sanitize_free_text(v)
        if v.startswith("-") or "--" in v:
            raise ValueError("Query starting with '-' or containing '--' is rejected.")
        return v


class CreateEventInput(BaseModel):
    """Validate inputs for ``khan_create_event``."""

    title: str = Field(min_length=1, max_length=MAX_TITLE_LEN)
    start: str = Field(min_length=1, max_length=MAX_SHORT_STR_LEN)
    end: str = Field(default="", max_length=MAX_SHORT_STR_LEN)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LEN)
    location: str = Field(default="", max_length=MAX_LOCATION_LEN)
    alarm: str = Field(default="", max_length=16)
    recurrence: str = Field(default="", max_length=16)

    @field_validator("alarm")
    @classmethod
    def _validate_alarm(cls, v: str) -> str:
        v = _sanitize_free_text(v)
        if v and not re.match(ALLOWED_ALARM_PATTERN, v):
            raise ValueError(f"Invalid alarm format '{v}'. Expected like '15m', '1h', '2d'.")
        return v

    @field_validator("recurrence")
    @classmethod
    def _validate_recurrence(cls, v: str) -> str:
        v = _sanitize_free_text(v)
        if v and v.lower() not in ALLOWED_RECURRENCE_VALUES:
            raise ValueError(
                f"Invalid recurrence '{v}'. Allowed: {sorted(ALLOWED_RECURRENCE_VALUES)}"
            )
        return v.lower()

    @field_validator("start", "end", "location", "description", "title")
    @classmethod
    def _reject_argument_injection(cls, v: str) -> str:
        v = _sanitize_free_text(v)
        if v and (v.startswith("-") or "--" in v):
            raise ValueError(
                "Inputs starting with '-' or containing '--' are rejected "
                "(argument-injection shield)."
            )
        return v


class UpdateEventInput(BaseModel):
    """Validate inputs for ``khan_update_event``."""

    old_term: str = Field(min_length=1, max_length=MAX_TITLE_LEN)
    new_title: str = Field(min_length=1, max_length=MAX_TITLE_LEN)
    new_start: str = Field(min_length=1, max_length=MAX_SHORT_STR_LEN)
    new_end: str = Field(default="", max_length=MAX_SHORT_STR_LEN)
    new_description: str = Field(default="", max_length=MAX_DESCRIPTION_LEN)
    new_location: str = Field(default="", max_length=MAX_LOCATION_LEN)

    @field_validator(
        "old_term",
        "new_title",
        "new_start",
        "new_end",
        "new_description",
        "new_location",
    )
    @classmethod
    def _reject_argument_injection(cls, v: str) -> str:
        v = _sanitize_free_text(v)
        if v and (v.startswith("-") or "--" in v):
            raise ValueError("Inputs starting with '-' or containing '--' are rejected.")
        return v


class DeleteEventInput(BaseModel):
    """Validate inputs for ``khan_delete_event`` / ``khan_delete_event_safe``."""

    exact_term: str = Field(min_length=1, max_length=MAX_TITLE_LEN)

    @field_validator("exact_term")
    @classmethod
    def _reject_argument_injection(cls, v: str) -> str:
        v = _sanitize_free_text(v)
        if v.startswith("-") or "--" in v:
            raise ValueError("Terms starting with '-' or containing '--' are rejected.")
        return v


class ViewAgendaInput(BaseModel):
    """Validate inputs for ``khan_view_agenda``."""

    period: Literal["today", "tomorrow", "7d", "30d"] = "7d"


class ViewCalendarInput(BaseModel):
    """Validate inputs for ``khan_view_calendar``."""

    reference_month: str = Field(default="today", max_length=MAX_SHORT_STR_LEN)

    @field_validator("reference_month")
    @classmethod
    def _sanitize_reference_month(cls, v: str) -> str:
        return _sanitize_free_text(v)


__all__ = [
    "ListEventsInput",
    "SearchEventsInput",
    "CreateEventInput",
    "UpdateEventInput",
    "DeleteEventInput",
    "ViewAgendaInput",
    "ViewCalendarInput",
]
