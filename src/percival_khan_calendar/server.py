"""Percival Khan Calendar MCP Server — entrypoint.

This module is intentionally thin: ~50 LOC. All real logic lives in
``models``, ``exceptions``, ``security``, ``lifecycle`` and the
``tools`` / ``adapters`` packages.
"""

from __future__ import annotations

import logging
import os

from fastmcp import FastMCP

from .adapters.khal_adapter import KhalAdapter
from .lifecycle import setup_workspace
from .tools import register_all_tools

logging.basicConfig(
    level=os.environ.get("KHAN_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("percival-khan-calendar")

mcp = FastMCP("percival-khan-calendar")


def main() -> None:
    """Boot the MCP server over stdio."""
    logger.info("Booting Percival Khan Calendar MCP Server...")
    try:
        setup_workspace()
    except OSError as exc:
        logger.error("Workspace bootstrap failed: %s", exc)
        raise
    adapter = KhalAdapter()
    register_all_tools(mcp, adapter)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
