"""Read tools: list and search events."""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.khal_adapter import EventMatch, KhalAdapter
from ..adapters.subprocess_runner import executar_comando_khal
from ..exceptions import KhanError
from ..models import ListEventsInput, SearchEventsInput
from ..security import envelope_untrusted_data


def register_list_events_tools(mcp: FastMCP, adapter: KhalAdapter) -> None:
    @mcp.tool("khan_list_events")
    def list_events(start_date: str = "today", range_or_end: str = "") -> str:
        """List scheduled events from the local calendar.

        Use this to see what is planned for a specific day, week, or
        period.

        Parameters:
        - start_date: Starting point for the list. Supports 'today',
          'tomorrow', 'now', or specific dates like 'DD/MM/YYYY'.
        - range_or_end (optional): Duration (e.g., '7d', '1w', '30d')
          or a specific end date ('DD/MM/YYYY').
        """
        params = ListEventsInput(
            start_date=start_date,
            range_or_end=range_or_end,
        )
        comando = ["list", params.start_date]
        if params.range_or_end:
            comando.append(params.range_or_end)
        try:
            res = executar_comando_khal(
                comando,
                tool_name="khan_list_events",
                retry_on_transient=True,
            )
        except KhanError as exc:
            return f"[recoverable_by_agent=true] {exc}"
        return envelope_untrusted_data(
            res.stdout or "No events found.",
            f"Agenda from {params.start_date}",
        )

    @mcp.tool("khan_search_events")
    def search_events(query: str) -> str:
        """Search for events across the entire calendar database using
        a keyword.

        Use this to locate specific events when the date is unknown.

        Parameters:
        - query: The keyword or phrase to search for (e.g., 'meeting',
          'dentist', 'Emily').
        """
        params = SearchEventsInput(query=query)
        matches: list[EventMatch] = adapter.find_event(params.query)
        if not matches:
            return envelope_untrusted_data(
                f"No events match '{params.query}'.",
                f"Search results for: {params.query}",
            )
        body = "\n".join(m.format() for m in matches)
        return envelope_untrusted_data(
            body,
            f"Search results for: {params.query}",
        )
