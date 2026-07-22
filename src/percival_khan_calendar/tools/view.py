"""View tools — agenda and calendar grid (delegated to khal CLI)."""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.subprocess_runner import executar_comando_khal
from ..constants import MAX_AGENDA_CHARS
from ..exceptions import KhanError
from ..models import ViewAgendaInput, ViewCalendarInput
from ..security import envelope_untrusted_data


def _short_render(title: str, body: str) -> str:
    """Render a chat-style body and truncate **to** the limit (not past).

    The previous implementation trimmed to ``MAX_AGENDA_CHARS`` and then
    appended a truncation marker, so the final output exceeded the
    budget. We now reserve room for the marker up-front.
    """
    _truncation_marker = "\n... [Conteúdo truncado.]\n```"
    budget = max(
        64,
        MAX_AGENDA_CHARS - len(_truncation_marker) - len(title) - 8,
    )
    rendered = f"{title}\n\n```text\n{body}\n```"
    if len(rendered) <= budget:
        return rendered
    trimmed_body = body[: max(0, budget - len(title) - 12)]
    return f"{title}\n\n```text\n{trimmed_body}{_truncation_marker}"


def register_view_tools(mcp: FastMCP) -> None:
    @mcp.tool("khan_view_agenda")
    def view_agenda_list(period: str = "7d") -> str:
        """Generate a clean agenda list view (text-based) optimized
        for chat interfaces. Shows upcoming events in chronological
        sequence.

        Parameters:
        - period: 'today', 'tomorrow', '7d' (next 7 days), or '30d'.
        """
        params = ViewAgendaInput(period=period)
        formato = "{start-end-time-style} {title}"
        # khal interprets `list <start> <range>`; when period == "today"
        # we want to ask for an explicit 1-day window instead of passing
        # the same "today" twice.
        if params.period == "today":
            comando = ["list", "today", "1d", "-f", formato]
        else:
            comando = ["list", "today", params.period, "-f", formato]
        try:
            res = executar_comando_khal(comando, tool_name="khan_view_agenda")
        except KhanError as exc:
            return f"{exc}"
        if not res.stdout:
            return envelope_untrusted_data("No events.", f"📅 Your Agenda ({params.period})")
        body = _short_render(f"📅 **Your Agenda ({params.period}):**", res.stdout)
        return envelope_untrusted_data(body, f"Your Agenda ({params.period})")

    @mcp.tool("khan_view_calendar")
    def view_calendar_grid(reference_month: str = "today") -> str:
        """Generate a visual matrix/grid view of the month.

        Best for viewing event density and identifying free/busy days.

        Parameters:
        - reference_month: 'today' (current month), or a specific
          date like '01/MM/YYYY'.
        """
        params = ViewCalendarInput(reference_month=reference_month)
        comando = ["calendar", params.reference_month]
        try:
            res = executar_comando_khal(comando, tool_name="khan_view_calendar")
        except KhanError as exc:
            return f"{exc}"
        if not res.stdout:
            return envelope_untrusted_data("No calendar data.", "🗓️ Monthly View")
        body = _short_render("🗓️ **Monthly View:**", res.stdout)
        return envelope_untrusted_data(body, "Monthly View")
