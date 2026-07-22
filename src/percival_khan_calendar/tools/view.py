"""View tools — agenda and calendar grid (delegated to khal CLI)."""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.subprocess_runner import executar_comando_khal
from ..constants import MAX_AGENDA_CHARS
from ..exceptions import KhanError
from ..models import ViewAgendaInput, ViewCalendarInput


def _short_render(title: str, body: str) -> str:
    """Common Telegram-style + envelope wrapping used by view tools."""
    rendered = (
        f"{title}\n\n"
        "```text\n"
        f"{body}\n"
        "```"
    )
    if len(rendered) > MAX_AGENDA_CHARS:
        rendered = (
            rendered[:MAX_AGENDA_CHARS]
            + "\n... [Conteúdo truncado.]\n```"
        )
    return rendered


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
        comando = ["list", "today", params.period, "-f", formato]
        try:
            res = executar_comando_khal(
                comando, tool_name="khan_view_agenda"
            )
        except KhanError as exc:
            return f"{exc}"
        if not res.stdout:
            return res.stdout or "No events."
        return _short_render(
            f"📅 **Your Agenda ({params.period}):**", res.stdout
        )

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
            res = executar_comando_khal(
                comando, tool_name="khan_view_calendar"
            )
        except KhanError as exc:
            return f"{exc}"
        if not res.stdout:
            return "No calendar data."
        return _short_render(
            "🗓️ **Monthly View:**", res.stdout
        )
