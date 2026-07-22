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
    """
    tool = asyncio.run(mcp.get_tool(name))
    return tool.fn
