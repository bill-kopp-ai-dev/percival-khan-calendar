"""Aggregate tool registration for the MCP server.

Each tool module exposes a single ``register_*_tools(mcp, adapter)``
function which decorates the tool functions onto the FastMCP app.
``register_all_tools`` is the single entry point used by ``server.py``.
"""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.khal_adapter import KhalAdapter


def register_all_tools(mcp: FastMCP, adapter: KhalAdapter) -> None:
    """Register all 8 original tools + 4 new (Phase 7) tools onto ``mcp``."""
    # Lazy imports avoid loading all sub-modules on package import.
    from .create_event import register_create_event_tools
    from .delete_event import register_delete_event_tools
    from .list_events import register_list_events_tools
    from .status import register_status_tools
    from .update_event import register_update_event_tools
    from .view import register_view_tools

    register_list_events_tools(mcp, adapter)
    register_create_event_tools(mcp, adapter)
    register_update_event_tools(mcp, adapter)
    register_delete_event_tools(mcp, adapter)
    register_view_tools(mcp)
    register_status_tools(mcp)


__all__ = ["register_all_tools"]
