"""Percival Khan Calendar MCP Server — entrypoint.

This module is intentionally thin: ~50 LOC. All real logic lives in
``models``, ``exceptions``, ``security``, ``lifecycle`` and the
``tools`` / ``adapters`` / ``resources`` packages.

The entrypoint wires:

* ``lifecycle.setup_workspace`` (auto-heal of khal.conf, idempotent)
* a single ``KhalAdapter`` instance shared by every tool
* the registered tools via ``register_all_tools``
* 6 ``prompts.primitives`` via ``register_prompts``
* 1 ``resources`` URI via ``register_resources``
"""

from __future__ import annotations

import logging
import os

from fastmcp import FastMCP

from .adapters.khal_adapter import KhalAdapter
from .lifecycle import setup_workspace
from .resources import register_resources
from .tools import register_all_tools, register_prompts

# Configure logging at module import time so child loggers (in
# adapters/, tools/) pick it up. ``logging.basicConfig`` is a no-op
# if the root logger already has handlers, which keeps ``server.py``
# re-importable under tests while still producing output for CLI use.
logging.basicConfig(
    level=os.environ.get("KHAN_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("percival-khan-calendar")

mcp = FastMCP("percival-khan-calendar")


def main() -> None:
    """Boot the MCP server over stdio.

    We construct a *fresh* ``FastMCP`` instance inside ``main``
    rather than relying on the module-level ``mcp`` global so the
    process is fully re-entrant: callers can ``import server``
    safely without polluting the registry of a future invocation.
    The module-level ``mcp`` is kept for documentation /
    inspection (``fastmcp dev`` style loaders); production boot
    always uses the local instance.
    """
    logger.info("Booting Percival Khan Calendar MCP Server...")
    try:
        setup_workspace()
    except OSError as exc:
        logger.error("Workspace bootstrap failed: %s", exc)
        raise
    boot_app = FastMCP("percival-khan-calendar")
    adapter = KhalAdapter()
    register_all_tools(boot_app, adapter)
    register_prompts(boot_app)
    register_resources(boot_app)
    boot_app.run(transport="stdio")


if __name__ == "__main__":
    main()
