"""Update tools — preserves UID and RRULE."""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.khal_adapter import KhalAdapter
from ..exceptions import KhanError
from ..models import UpdateEventInput
from ..security import envelope_untrusted_data


def register_update_event_tools(mcp: FastMCP, adapter: KhalAdapter) -> None:
    @mcp.tool("khan_update_event")
    def update_event(
        old_term: str,
        new_title: str,
        new_start: str,
        new_end: str = "",
        new_description: str = "",
        new_location: str = "",
    ) -> str:
        """Update an existing event in place — preserves UID, RRULE and
        VALARM (does NOT delete-and-recreate).

        Parameters:
        - old_term: Unique identifier of the event to be changed.
        - new_title, new_start, new_end, new_description, new_location:
          New details. Empty string = leave unchanged.
        """
        params = UpdateEventInput(
            old_term=old_term,
            new_title=new_title,
            new_start=new_start,
            new_end=new_end,
            new_description=new_description,
            new_location=new_location,
        )
        try:
            updated = adapter.update_event(
                params.old_term,
                fields={
                    "summary": params.new_title,
                    "dtstart": params.new_start,
                    "dtend": params.new_end,
                    "description": params.new_description,
                    "location": params.new_location,
                },
            )
        except KhanError as exc:
            return f"{exc}"

        body = f"Updated event {updated.format()} [uid={updated.uid}]\nUID and RRULE preserved."
        return envelope_untrusted_data(body, f"Updated: {updated.summary}")
