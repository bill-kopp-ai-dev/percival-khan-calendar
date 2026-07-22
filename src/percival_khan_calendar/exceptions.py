"""Typed exceptions for the calendar MCP server.

These let the agent distinguish recoverable errors from infrastructure faults.
"""

from __future__ import annotations


class KhanError(Exception):
    """Base exception. All calendar errors derive from this."""


class KhanValidationError(KhanError, ValueError):
    """Raised when an input fails validation (Pydantic or khal argparse).

    Recoverable by the agent: reformulate the input.
    """


class KhanNotFoundError(KhanError, LookupError):
    """Raised when a queried event/term does not match anything."""


class KhanAmbiguousMatchError(KhanError):
    """Raised when a search matches multiple events.

    Recoverable by the agent: provide a more specific identifier.
    Contains ``matches: list[str]`` with the candidates.
    """

    def __init__(self, term: str, matches: list[str]):
        self.term = term
        self.matches = matches
        super().__init__(f"Ambiguous match for '{term}': {len(matches)} candidates: {matches[:3]}")


class KhanInfrastructureError(KhanError, RuntimeError):
    """Raised when the underlying khal binary or DB is unavailable.

    NOT recoverable by the agent — escalate to operator.
    """


class KhanLockError(KhanError, RuntimeError):
    """Raised when the workspace is locked by another process."""


__all__ = [
    "KhanError",
    "KhanValidationError",
    "KhanNotFoundError",
    "KhanAmbiguousMatchError",
    "KhanInfrastructureError",
    "KhanLockError",
]
