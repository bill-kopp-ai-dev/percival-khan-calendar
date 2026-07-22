"""Create tools."""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.khal_adapter import KhalAdapter
from ..exceptions import KhanError
from ..models import CreateEventInput
from ..security import envelope_untrusted_data


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
        params = CreateEventInput(
            title=title,
            start=start,
            end=end,
            description=description,
            location=location,
            alarm=alarm,
            recurrence=recurrence,
        )
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
