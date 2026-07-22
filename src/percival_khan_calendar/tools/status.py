"""Status & auxiliary tools (Phase 7 additions)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastmcp import FastMCP

from .. import constants
from ..adapters.locks import workspace_lock
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

        # 1. Compute paths BEFORE any I/O so we don't expose partial
        # writes on error. The "user-supplied" path MUST be checked
        # for symlinks *as written* (before resolution) so a redirect
        # is caught at the source rather than at the resolved target.
        if not output_path:
            output_path = str(constants.WORKSPACE_DIR / "export.ics")
        try:
            workspace = constants.WORKSPACE_DIR.resolve()
            output_unresolved = Path(output_path)
            try:
                lstat = output_unresolved.lstat()
                if (lstat.st_mode & 0o170000) == 0o120000:
                    return "Refused: output_path must not be a symlink."
            except FileNotFoundError:
                # Fine — we will create the file. The symlink check
                # only applies to pre-existing entries.
                pass
            # ``strict=False`` so we accept yet-to-be-created output
            # paths inside the workspace.
            output = output_unresolved.resolve(strict=False)
            output.relative_to(workspace)  # path-traversal guard
        except (OSError, ValueError):
            return "Refused: output_path must be inside the workspace."

        # 2. Read all source events inside the workspace lock so a
        # concurrent writer doesn't produce an inconsistent snapshot.
        try:
            with workspace_lock(blocking=True):
                cal = Calendar()
                cal.add("prodid", "-//percival-khan-calendar//EN")
                cal.add("version", "2.0")
                for ics in constants.DATA_DIR.rglob("*.ics"):
                    sub = Calendar.from_ical(ics.read_bytes())
                    for ev in sub.walk():
                        cal.add_component(ev)
                # Write atomically to avoid leaving an empty .ics on
                # mid-flight failure. _atomic_write_ics fsync's both
                # file and parent directory for durability.
                from ..adapters.khal_adapter import _atomic_write_ics

                _atomic_write_ics(output, cal)
        except (OSError, ValueError, TypeError) as exc:
            # Sanitized error: do NOT leak internal stack frames,
            # paths from exception messages, or icalendar internals
            # to the agent. Just the exception class is enough to debug.
            logger.exception("khan_export_ics failed")
            return f"[recoverable_by_agent=false] export failed: {type(exc).__name__}"
        return f"Exported to {output}."
