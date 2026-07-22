"""Aggregate tool and prompt registration for the MCP server.

Each tool module exposes a single ``register_*_tools(mcp, adapter)``
function which decorates the tool functions onto the FastMCP app.
``register_all_tools`` is the single entry point used by ``server.py``
for tools; ``register_prompts`` is the entry point for the 6
MCP prompt primitives.
"""

from __future__ import annotations

from fastmcp import FastMCP

from ..adapters.khal_adapter import KhalAdapter


def register_all_tools(mcp: FastMCP, adapter: KhalAdapter) -> None:
    """Register all 12 tools onto ``mcp`` (Phase 7 tool family)."""
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


# Re-export the prompt registrar so ``server.py`` can call it
# via ``from .tools import register_prompts``.
from .prompts import register_prompts  # noqa: E402

__all__ = ["register_all_tools", "register_prompts"]
