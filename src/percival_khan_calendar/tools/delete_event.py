"""Delete tools — safe by default; explicit confirm for actual delete."""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import ValidationError

from ..adapters.khal_adapter import KhalAdapter
from ..exceptions import KhanAmbiguousMatchError, KhanError, KhanNotFoundError
from ..models import DeleteEventInput
from ..security import envelope_untrusted_data


def _validation_error_response(exc: ValidationError, tool: str) -> str:
    """Return a LLM-friendly message from a pydantic validation failure.

    We choose to convert it to a string instead of letting the exception
    bubble up so that the agent gets a structured hint about what to
    fix rather than a traceback.
    """
    # pydantic v2 exposes errors() as a list[dict].
    field_errors = "; ".join(
        f"{'.'.join(str(p) for p in err.get('loc', ()))}: {err.get('msg', '')}"
        for err in exc.errors()
    )
    return f"[recoverable_by_agent=true] {tool} rejected the input: {field_errors}"


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
        try:
            params = DeleteEventInput(exact_term=exact_term)
        except ValidationError as exc:
            return _validation_error_response(exc, "khan_delete_event")
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

        Notes:
          Dry-run report and actual delete both happen inside the
          workspace lock, so a concurrent agent cannot delete the same
          event twice between the report and the confirmation.
        """
        try:
            params = DeleteEventInput(exact_term=exact_term)
        except ValidationError as exc:
            return _validation_error_response(exc, "khan_delete_event_safe")
        try:
            outcome = adapter.delete_event_safe(params.exact_term, confirm=confirm)
        except (KhanAmbiguousMatchError, KhanNotFoundError) as exc:
            return envelope_untrusted_data(f"Refused: {exc}", "Delete dry-run")
        except KhanError as exc:
            return f"{exc}"
        return envelope_untrusted_data(outcome, "Delete")

    @mcp.tool("khan_get_event")
    def get_event(exact_term: str) -> str:
        """Return a single event's full details for inspection."""
        try:
            params = DeleteEventInput(exact_term=exact_term)
        except ValidationError as exc:
            return _validation_error_response(exc, "khan_get_event")
        try:
            m = adapter.find_event_unique(params.exact_term)
        except (KhanNotFoundError, KhanAmbiguousMatchError) as exc:
            return f"{exc}"
        body = (
            f"UID: {m.uid}\nSummary: {m.summary}\nDescription: "
            f"{m.description}\nFile: {m.filepath.name}"
        )
        return envelope_untrusted_data(body, f"Event: {m.summary}")
