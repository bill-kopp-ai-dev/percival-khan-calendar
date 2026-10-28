"""Configuration-aware process entrypoint."""

from __future__ import annotations

import sys


def main() -> int:
    """Validate environment configuration before importing the server."""
    try:
        from . import constants  # noqa: F401
    except ValueError as exc:
        print(f"Invalid server configuration: {exc}", file=sys.stderr)
        return 2

    from .server import main as server_main

    return server_main()
