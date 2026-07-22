"""Delete tools — safe by default; explicit confirm for actual delete."""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.khal_adapter import KhalAdapter
from ..exceptions import KhanError, KhanNotFoundError
from ..models import DeleteEventInput
from ..security import envelope_untrusted_data


def register_delete_event_tools(mcp: FastMCP, adapter: KhalAdapter) -> None:
    @mcp.tool("khan_delete_event")
    def delete_event(exact_term: str) -> str:
        """Permanently remove an event from the calendar.

        Prefer ``khan_delete_event_safe`` for a dry-run.

        Parameters:
        - exact_term: A unique identifier (part of title or
          description). Must be specific enough to avoid accidental
          deletion of multiple events.
        """
        params = DeleteEventInput(exact_term=exact_term)
        try:
            n = adapter.delete_event(params.exact_term)
        except KhanError as exc:
            return f"{exc}"
        return envelope_untrusted_data(
            f"Deleted event matching '{params.exact_term}' ({n} file).",
            "Delete",
        )

    @mcp.tool("khan_delete_event_safe")
    def delete_event_safe(exact_term: str, confirm: bool = False) -> str:
        """Dry-run by default; set ``confirm=True`` to actually delete.

        Parameters:
        - exact_term: Unique identifier of the event.
        - confirm: If False (default), only reports the matched event
          so the agent can show the user what would be deleted.
        """
        DeleteEventInput(exact_term=exact_term)
        matches = adapter.find_event(exact_term)
        if len(matches) != 1:
            return envelope_untrusted_data(
                "Refused: "
                + ("no matches" if not matches else f"{len(matches)} matches")
                + "\nCandidates:\n"
                + "\n".join(f"- [{m.uid}] {m.summary}" for m in matches[:10]),
                "Delete dry-run",
            )
        m = matches[0]
        if not confirm:
            return envelope_untrusted_data(
                "Dry run. Will delete:\n"
                f"- UID: {m.uid}\n"
                f"- Summary: {m.summary}\n"
                f"- File: {m.filepath.name}\n"
                "Set confirm=True to actually delete.",
                "Delete dry-run",
            )
        try:
            adapter.delete_event(exact_term)
        except KhanError as exc:
            return f"{exc}"
        return envelope_untrusted_data(f"Deleted event with UID {m.uid}.", "Delete")

    @mcp.tool("khan_get_event")
    def get_event(exact_term: str) -> str:
        """Return a single event's full details for inspection."""
        DeleteEventInput(exact_term=exact_term)
        try:
            m = adapter.find_event_unique(exact_term)
        except KhanNotFoundError as exc:
            return f"{exc}"
        body = (
            f"UID: {m.uid}\nSummary: {m.summary}\nDescription: "
            f"{m.description}\nFile: {m.filepath.name}"
        )
        return envelope_untrusted_data(body, f"Event: {m.summary}")
