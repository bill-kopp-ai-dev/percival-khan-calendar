"""Test helpers for invoking registered MCP tools synchronously."""

from __future__ import annotations

import asyncio
from typing import Any, Callable


def get_tool_fn(mcp, name: str) -> Callable[..., Any]:
    """Return the underlying Python function for a registered tool.

    FastMCP 3.x exposes tool metadata only via async APIs. To keep
    tests simple and synchronous (matching the rest of the suite), we
    reach into the FunctionTool's ``fn`` attribute after fetching it
    once via the async ``get_tool`` coroutine.

    Raises:
        LookupError: if ``name`` is not a registered tool on ``mcp``.
            We re-raise the FastMCP lookup failure as a more
            descriptive error instead of letting ``AttributeError``
            leak from ``tool.fn``.
    """
    try:
        tool = asyncio.run(mcp.get_tool(name))
    except Exception as exc:
        raise LookupError(f"Tool '{name}' not found or get_tool failed: {exc}") from exc
    if tool is None:
        raise LookupError(f"Tool '{name}' returned None from get_tool().")
    fn = getattr(tool, "fn", None)
    if fn is None:
        raise LookupError(
            f"Tool '{name}' exists but has no .fn attribute (type={type(tool).__name__})."
        )
    return fn
