"""Hardened subprocess runner for the khal CLI.

Responsibilities:
  - Inject ``-c <CONF_FILE>`` automatically.
  - Enforce a timeout (configurable via ``KHAN_SUBPROCESS_TIMEOUT``).
  - Map subprocess failures to typed exceptions.
  - Emit structured JSON logs (``event``, ``tool``, ``returncode``,
    ``elapsed_ms``).
  - Optionally retry idempotent commands only (refuses
    ``new``/``delete``/``edit``).
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass

from ..constants import CONF_FILE, DEFAULT_SUBPROCESS_TIMEOUT
from ..exceptions import (
    KhanInfrastructureError,
    KhanValidationError,
)

logger = logging.getLogger("percival-khan-calendar.runner")


@dataclass(frozen=True, slots=True)
class KhalResult:
    """Result of a hardened khal subprocess call."""

    stdout: str
    returncode: int
    elapsed_ms: int

    def __bool__(self) -> bool:  # convenience: empty stdout = falsy
        return bool(self.stdout)


# Commands safe to retry on transient infrastructure errors.
_IDEMPOTENT_SUBCOMMANDS: frozenset[str] = frozenset(
    {"list", "search", "agenda", "calendar", "printics", "printcalendars", "show"}
)


def executar_comando_khal(
    comando: list[str],
    *,
    tool_name: str = "unknown",
    timeout: float = DEFAULT_SUBPROCESS_TIMEOUT,
    retry_on_transient: bool = False,
    max_retries: int = 2,
) -> KhalResult:
    """Run a khal CLI command with hardening.

    Args:
        comando: e.g. ``["list", "today"]`` (without ``-c`` which is injected).
        tool_name: Used for structured logs.
        timeout: Seconds before ``KhanInfrastructureError`` is raised.
        retry_on_transient: If True, retry up to ``max_retries`` times on
            ``KhanInfrastructureError``. Only for idempotent commands.
        max_retries: Upper bound for retries when enabled.

    Returns:
        ``KhalResult`` with stdout, returncode, elapsed_ms.

    Raises:
        KhanValidationError: argparse/validation errors (recoverable).
        KhanInfrastructureError: missing binary, timeout, or generic khal
            failure (NOT recoverable).
    """
    if retry_on_transient and comando and comando[0] not in _IDEMPOTENT_SUBCOMMANDS:
        logger.warning(
            "Refusing to retry non-idempotent subcommand %r",
            comando[0],
        )
        retry_on_transient = False

    full_cmd = ["khal", "-c", str(CONF_FILE), *comando]
    attempts = max_retries if retry_on_transient else 0
    last_error: KhanInfrastructureError | None = None

    for attempt in range(attempts + 1):
        start = time.monotonic()
        try:
            proc = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            _log_event(
                tool=tool_name,
                cmd=full_cmd[:6],
                returncode=proc.returncode,
                elapsed_ms=elapsed_ms,
                attempt=attempt,
            )

            if proc.returncode == 0:
                return KhalResult(
                    stdout=(proc.stdout or "").strip(),
                    returncode=0,
                    elapsed_ms=elapsed_ms,
                )

            stderr = (proc.stderr or "").strip()
            if (
                proc.returncode == 2
                or "Usage:" in stderr
                or "error:" in stderr.lower()
                or "invalid" in stderr.lower()
            ):
                raise KhanValidationError(f"khal rejected the command: {stderr or proc.stdout}")

            last_error = KhanInfrastructureError(
                f"khal exited with code {proc.returncode}: {stderr}"
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            last_error = KhanInfrastructureError(
                f"khal timed out after {timeout}s: {' '.join(full_cmd)}"
            )
            logger.error(
                json.dumps(
                    {
                        "event": "subprocess.timeout",
                        "tool": tool_name,
                        "cmd": full_cmd[:6],
                        "timeout": timeout,
                        "attempt": attempt,
                    }
                )
            )
        except FileNotFoundError as exc:
            raise KhanInfrastructureError(
                "khal binary not found in PATH. Install with `uv pip install khal`."
            ) from exc
        except OSError as exc:
            raise KhanInfrastructureError(f"OS error running khal: {exc}") from exc

    assert last_error is not None  # only reached if not raised above
    raise last_error


def _log_event(
    *,
    tool: str,
    cmd: list[str],
    returncode: int,
    elapsed_ms: int,
    attempt: int,
) -> None:
    """Emit one JSON log line per call (when log level permits)."""
    logger.info(
        json.dumps(
            {
                "event": "khal.call",
                "tool": tool,
                "cmd": cmd,
                "returncode": returncode,
                "elapsed_ms": elapsed_ms,
                "attempt": attempt,
            }
        )
    )


__all__ = ["executar_comando_khal", "KhalResult"]
