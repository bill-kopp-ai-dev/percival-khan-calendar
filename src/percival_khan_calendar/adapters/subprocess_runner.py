"""Hardened subprocess runner for the khal CLI.

Responsibilities:
  - Inject ``-c <CONF_FILE>`` automatically.
  - Enforce a timeout (configurable via ``KHAN_SUBPROCESS_TIMEOUT``).
  - Decode stdout/stderr as UTF-8 (replace errors) so a stray non-ASCII
    byte can't crash the whole tool.
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


def _safe_log_cmd(cmd: list[str]) -> list[str]:
    """Strip the command to a log-safe representation.

    The first six positional args capture the subcommand and its
    unchanging prefix (khal, -c, <conf>). The remaining args usually
    carry user-supplied terms (date strings, search terms) and may
    contain sensitive context about the user's calendar — we replace
    them with an ellipsis so logs stay hermetic.
    """
    head = list(cmd[:6])
    if len(cmd) > 6:
        head.append("...")
    return head


def _decode(data: bytes | str | None) -> str:
    """Decode subprocess output as UTF-8, replacing malformed bytes.

    A bare ``text=True`` would crash with UnicodeDecodeError on a
    stray non-UTF-8 byte coming out of khal; we want a lossy
    conversion that returns *something* the agent can act on.
    """
    if data is None:
        return ""
    if isinstance(data, str):
        return data.strip()
    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        logger.warning("khal emitted non-UTF-8 bytes; replacing malformed sequences")
        return data.decode("utf-8", errors="replace").strip()


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
    log_cmd = _safe_log_cmd(full_cmd)
    attempts = max_retries if retry_on_transient else 0
    last_error: KhanInfrastructureError | None = None

    for attempt in range(attempts + 1):
        start = time.monotonic()
        try:
            # Capture raw bytes; we decode manually below so a stray
            # non-UTF-8 byte cannot crash the tool.
            # ``env={**os.environ, ...}`` inherits ``TZ`` from the parent
            # so `khal list`/`agenda`/`calendar` render each UTC-stored
            # ``DTSTART`` (see khal_adapter._parse_khal_time) back into
            # the same local wall-clock time the agent's operator
            # expects, rather than whatever TZ the subprocess happens
            # to default to. ``LC_ALL`` is pinned to ``C.UTF-8``
            # (overriding whatever locale the parent has) so stdout/
            # stderr decoding and khal's own CLI messages are
            # deterministic across environments.
            import os

            inherit_env = {**os.environ, "LC_ALL": "C.UTF-8"}
            proc = subprocess.run(
                full_cmd,
                capture_output=True,
                timeout=timeout,
                check=False,
                env=inherit_env,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            _log_event(
                tool=tool_name,
                cmd=log_cmd,
                returncode=proc.returncode,
                elapsed_ms=elapsed_ms,
                attempt=attempt,
            )

            if proc.returncode == 0:
                return KhalResult(
                    stdout=_decode(proc.stdout),
                    returncode=0,
                    elapsed_ms=elapsed_ms,
                )

            stderr = _decode(proc.stderr)
            if (
                proc.returncode == 2
                or "Usage:" in stderr
                or "error:" in stderr.lower()
                or "invalid" in stderr.lower()
            ):
                raise KhanValidationError(
                    f"khal rejected the command: {stderr or _decode(proc.stdout)}"
                )

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
                        "cmd": log_cmd,
                        "timeout": timeout,
                        "attempt": attempt,
                    }
                )
            )
        except FileNotFoundError as exc:
            # The khal binary is missing. ``retry_on_transient``
            # (restricted to idempotent commands) makes sense here
            # because the agent might have just installed khal — and
            # the list/agenda commands are inherently idempotent.
            # But the *message* still names the binary so a
            # permanent misconfiguration is clearly the user's fault.
            last_error = KhanInfrastructureError(
                "khal binary not found in PATH. Install with `uv pip install khal`."
            )
            logger.warning(
                json.dumps(
                    {
                        "event": "subprocess.missing_binary",
                        "tool": tool_name,
                        "exc": str(exc),
                        "attempt": attempt,
                    }
                )
            )
        except PermissionError as exc:
            last_error = KhanInfrastructureError(
                f"khal binary not executable (permission denied): {exc}"
            )
        except OSError as exc:
            last_error = KhanInfrastructureError(f"OS error running khal: {exc}")
            last_error.__cause__ = exc

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
