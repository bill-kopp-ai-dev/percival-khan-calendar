"""Create tools."""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import ValidationError

from ..adapters.khal_adapter import KhalAdapter
from ..exceptions import KhanError
from ..models import CreateEventInput
from ..security import envelope_untrusted_data


def _validation_error_response(exc: ValidationError, tool: str) -> str:
    """Return a structured, recoverable error string from a Pydantic failure."""
    field_errors = "; ".join(
        f"{'.'.join(str(p) for p in err.get('loc', ()))}: {err.get('msg', '')}"
        for err in exc.errors()
    )
    return f"[recoverable_by_agent=true] {tool} rejected the input: {field_errors}"


def register_create_event_tools(mcp: FastMCP, adapter: KhalAdapter) -> None:
    @mcp.tool("khan_create_event")
    def create_event(
        title: str,
        start: str,
        end: str = "",
        description: str = "",
        location: str = "",
        alarm: str = "",
        recurrence: str = "",
    ) -> str:
        """Create a new event or appointment in the user's local
        calendar.

        Parameters:
        - title (Required): Name of the event.
        - start (Required): Start date and/or time. Supports
          'today 14:00', 'tomorrow', 'DD/MM/YYYY HH:MM', or just
          'HH:MM'.
        - end (Optional): End date/time or duration.
        - description (Optional): Additional notes or details.
        - location (Optional): Where the event takes place.
        - alarm (Optional): Alert lead time (e.g., '15m', '1h', '2d').
        - recurrence (Optional): 'daily', 'weekly', 'monthly' or
          'yearly'.
        """
        try:
            params = CreateEventInput(
                title=title,
                start=start,
                end=end,
                description=description,
                location=location,
                alarm=alarm,
                recurrence=recurrence,
            )
        except ValidationError as exc:
            return _validation_error_response(exc, "khan_create_event")
        try:
            match = adapter.write_event(
                title=params.title,
                start=params.start,
                end=params.end,
                description=params.description,
                location=params.location,
                alarm=params.alarm,
                recurrence=params.recurrence,
            )
        except KhanError as exc:
            return f"{exc}"

        body = f"Created event {match.format()} [uid={match.uid}]"
        return envelope_untrusted_data(body, f"Created: {match.summary}")
