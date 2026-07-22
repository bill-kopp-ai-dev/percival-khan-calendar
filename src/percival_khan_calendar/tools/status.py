"""Status & auxiliary tools (Phase 7 additions)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastmcp import FastMCP

from .. import constants
from ..adapters.subprocess_runner import executar_comando_khal
from ..exceptions import KhanError
from ..security import envelope_untrusted_data

logger = logging.getLogger("percival-khan-calendar.tools.status")


def _workspace_status() -> str:
    ws = constants.WORKSPACE_DIR
    data = constants.DATA_DIR
    return (
        f"Workspace: {ws} ({'exists' if ws.exists() else 'absent'})\n"
        f"Data dir:  {data} ({'exists' if data.exists() else 'absent'})\n"
        f"khal.conf: {constants.CONF_FILE} "
        f"({'exists' if constants.CONF_FILE.exists() else 'absent'})\n"
        f"Lock:      {'enabled' if constants.ENABLE_LOCK else 'disabled'}"
    )


def register_status_tools(mcp: FastMCP) -> None:
    @mcp.tool("khan_get_status")
    def health_check() -> str:
        """Check the operational status of the calendar server."""
        return f"Percival Khan Calendar Server operational.\n{_workspace_status()}"

    @mcp.tool("khan_list_calendars")
    def list_calendars() -> str:
        """List the calendars configured in khal.conf."""
        try:
            res = executar_comando_khal(["printcalendars"], tool_name="khan_list_calendars")
        except KhanError as exc:
            return f"{exc}"
        return envelope_untrusted_data(res.stdout or "(no calendars)", "Available calendars")

    @mcp.tool("khan_export_ics")
    def export_ics(output_path: str = "") -> str:
        """Export the entire nanobot calendar to a single .ics file.

        Parameters:
        - output_path: absolute or relative path inside the workspace.
          Empty defaults to ``<WORKSPACE_DIR>/export.ics``.
        """
        from icalendar import Calendar

        if not output_path:
            output_path = str(constants.WORKSPACE_DIR / "export.ics")
        output = Path(output_path).resolve()
        # Path-traversal guard: must stay inside the workspace.
        try:
            output.relative_to(constants.WORKSPACE_DIR.resolve())
        except ValueError:
            return "Refused: output_path must be inside the workspace."

        try:
            cal = Calendar()
            cal.add("prodid", "-//percival-khan-calendar//EN")
            cal.add("version", "2.0")
            for ics in constants.DATA_DIR.rglob("*.ics"):
                sub = Calendar.from_ical(ics.read_bytes())
                for ev in sub.walk():
                    cal.add_component(ev)
            output.write_bytes(cal.to_ical())
        except Exception as exc:
            return f"{type(exc).__name__}: {exc}"
        return f"Exported to {output}."
