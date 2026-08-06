"""Read tools: list and search events."""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import ValidationError

from ..adapters.khal_adapter import EventMatch, KhalAdapter
from ..adapters.subprocess_runner import executar_comando_khal
from ..date_normalization import normalize_date_to_br
from ..exceptions import KhanError
from ..models import ListEventsInput, SearchEventsInput
from ..security import envelope_untrusted_data


def _validation_error_response(exc: ValidationError, tool: str) -> str:
    """Return a structured, recoverable error string from a Pydantic failure."""
    field_errors = "; ".join(
        f"{'.'.join(str(p) for p in err.get('loc', ()))}: {err.get('msg', '')}"
        for err in exc.errors()
    )
    return f"[recoverable_by_agent=true] {tool} rejected the input: {field_errors}"


def register_list_events_tools(mcp: FastMCP, adapter: KhalAdapter) -> None:
    @mcp.tool("khan_list_events")
    def list_events(start_date: str = "today", range_or_end: str = "") -> str:
        """List scheduled events from the local calendar.

        Use this to see what is planned for a specific day, week, or
        period.

        Parameters:
        - start_date: Starting point for the list. Supports 'today',
          'tomorrow', 'now', or specific dates like 'DD/MM/YYYY' or
          'YYYY-MM-DD' (ISO). ISO is normalized to the workspace's
          configured ``dateformat`` (typically ``DD/MM/YYYY``) before
          being passed to khal.
        - range_or_end (optional): Duration (e.g., '7d', '1w', '30d')
          or a specific end date ('DD/MM/YYYY' or 'YYYY-MM-DD').
        """
        try:
            params = ListEventsInput(
                start_date=start_date,
                range_or_end=range_or_end,
            )
        except ValidationError as exc:
            return _validation_error_response(exc, "khan_list_events")
        # Round-8 fix (issue 2026-08-06-khan-list-events-date-parsing):
        # khal 0.14.0 with `dateformat = %d/%m/%Y` rejects ISO dates like
        # ``2026-08-06`` with ``critical: Could not parse``. We translate
        # ISO to BR here so callers can use either form. Pass-through for
        # relative terms (``today``/``tomorrow``/``now``), durations
        # (``7d``/``1w``/``30d``), and BR literals — those don't depend
        # on the configured dateformat.
        start_normalized = normalize_date_to_br(params.start_date)
        end_normalized = normalize_date_to_br(params.range_or_end)
        comando = ["list", start_normalized]
        if end_normalized:
            comando.append(end_normalized)
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
        try:
            params = SearchEventsInput(query=query)
        except ValidationError as exc:
            return _validation_error_response(exc, "khan_search_events")
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
