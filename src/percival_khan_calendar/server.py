"""Percival Khan Calendar MCP Server — entrypoint.

This module is intentionally thin: ~70 LOC. All real logic lives in
``models``, ``exceptions``, ``security``, ``lifecycle`` and the
``tools`` / ``adapters`` / ``resources`` packages.

The entrypoint wires:

* ``lifecycle.setup_workspace`` (auto-heal of khal.conf, idempotent)
* a single ``KhalAdapter`` instance shared by every tool
* the registered tools via ``register_all_tools``
* 6 ``prompts.primitives`` via ``register_prompts``
* 1 ``resources`` URI via ``register_resources``
* a small CLI (``--version``/``--help``) used by the Docker smoke
  test and by humans exploring the binary.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from fastmcp import FastMCP

from . import __version__
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


def _build_parser() -> argparse.ArgumentParser:
    """Parse the small CLI surface used by humans and the Docker smoke.

    Only ``--version`` and ``--help`` are honoured; anything else is
    forwarded as the launch signal for the MCP server (FastMCP's own
    argument parser takes over).
    """
    parser = argparse.ArgumentParser(
        prog="percival-khan-calendar",
        description="Percival Khan Calendar MCP server (stdio transport).",
        add_help=False,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the package version and exit.",
    )
    parser.add_argument(
        "--help",
        "-h",
        action="store_true",
        help="Show this help message and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Boot the MCP server over stdio.

    We construct a *fresh* ``FastMCP`` instance inside ``main``
    rather than relying on the module-level ``mcp`` global so the
    process is fully re-entrant: callers can ``import server``
    safely without polluting the registry of a future invocation.
    The module-level ``mcp`` is kept for documentation /
    inspection (``fastmcp dev`` style loaders); production boot
    always uses the local instance.

    Returns:
        Process exit code. ``0`` for a clean run; ``1`` for a handled
        bootstrap failure or an unknown CLI flag. The MCP server
        itself never returns here while running — FastMCP blocks on
        stdio until the client closes the connection.
    """
    args, _unknown = _build_parser().parse_known_args(argv)
    if args.version:
        print(f"Percival Khan Calendar MCP Server version {__version__}")
        return 0
    if args.help:
        _build_parser().print_help()
        print(
            "\nOnce running, the server speaks Model Context Protocol over\n"
            "stdin/stdout. Connect any MCP-aware client (Nanobot, opencode,\n"
            "Claude Desktop, VS Code, Docker MCP Toolkit, …) to the running\n"
            "process to discover 12 tools, 6 prompts and 1 resource."
        )
        return 0

    logger.info("Booting Percival Khan Calendar MCP Server...")
    try:
        setup_workspace()
    except OSError as exc:
        logger.error("Workspace bootstrap failed: %s", exc)
        return 1
    boot_app = FastMCP("percival-khan-calendar")
    adapter = KhalAdapter()
    register_all_tools(boot_app, adapter)
    register_prompts(boot_app)
    register_resources(boot_app)
    boot_app.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
