# 🤖 Percival Khan Calendar — percival.OS MCP

**Version 0.3.0**

[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![Tests](https://img.shields.io/badge/tests-181%2F181-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-87.17%25-green.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)

## 📋 Description

**Percival Khan Calendar** is an MCP server that gives the Nanobot
agent autonomous, persistent, and secure capabilities to manage a local
calendar on top of the `khal` library.

This server is part of the **percival.OS** ecosystem — a Personal
Agentic Operating System designed for autonomy, security, and absolute
privacy.

As of **v0.3.0** the server exposes a complete MCP surface:
- **12 tools** for CRUD + visualisation + admin,
- **6 prompt primitives** to inject workflows and field semantics
  into the agent's reasoning,
- **1 text/markdown resource** (`khan://schema/main`) for on-demand
  technical reference.

---

## 🛡️ percival.OS Principles

Like every component of `percival.OS`, this MCP server strictly follows our core principles:

- **Local-First & Private**: Operates entirely on the local
  filesystem. Your appointments are never sent to the cloud
  without your explicit consent.
- **Data Sovereignty**: The calendar is stored in your
  infrastructure, ensuring your schedule remains private.
- **Hardened Security**: We implement "Prompt Injection Shields"
  by wrapping calendar data in XML tags and providing explicit
  instructions to the LLM to prevent indirect manipulation.
  Free-text inputs go through a Pydantic argument-injection
  guard (rejects leading `-` and `--` substrings).
- **Transparency**: Open-source and auditable to ensure full
  governance of your data.

---

## 🚀 Tools

The server offers complete CRUD, visualisation, and admin tools.

### Read

| Tool | Description |
|---|---|
| `khan_list_events` | List events in a window (``today``/``tomorrow``/``DD/MM/YYYY`` + ``7d``/``1d``). |
| `khan_search_events` | Full-text substring search across the calendar. |
| `khan_get_event` | Inspect a single event's full details (UID, file, RRULE). |
| `khan_view_agenda` | Chat-friendly agenda list (mobile/Telegram format). |
| `khan_view_calendar` | Visual ASCII month grid with bullet markers. |
| `khan_list_calendars` | List calendars configured in `khal.conf`. |
| `khan_get_status` | Operational status incl. workspace + conf drift detection. |

### Mutate

| Tool | Description |
|---|---|
| `khan_create_event` | Create events with alarms, recurrence, location, description. |
| `khan_update_event` | In-place update preserving UID, RRULE, VALARM. |
| `khan_delete_event` | Permanently remove an event. |
| `khan_delete_event_safe` | **Two-call dry-run + confirm** protocol (default safe). |
| `khan_export_ics` | Merge all events into a single `.ics` export. |

Total: **12 tools**.

---

## 🧭 MCP Prompts (v0.3.0)

The server registers **6 prompt primitives** that the agent can pull
via `prompts/get` whenever it needs explicit guidance on workflows or
field semantics that don't fit in a one-sentence tool description.

| Prompt | Args | When to use |
|---|---|---|
| `khan_overview` | — | Start of session; full server tour + workflow |
| `khan_create_event_semantics` | — | Pre-flight for `khan_create_event` (time/alarm/recurrence syntax) |
| `khan_update_workflow` | — | UID/RRULE/VALARM preservation rules |
| `khan_delete_with_confirmation` | — | Two-call dry-run + confirm protocol |
| `khan_search_strategy` | `keyword: str`, `scope: Literal[summary\|location\|description]="summary"` | Field-qualified substring search |
| `khan_quick_action_quick_create` | `user_intent: str` | Verbatim echo + PT-BR date mapping for free-form intents |

Example usage from a tool-calling agent:

```python
rendered = mcp.get_prompt(
    "khan_quick_action_quick_create",
    {"user_intent": "dentista amanhã 10h"},
)
# rendered.messages[0].content contains the verbatim intent + mapping hints
```

---

## 📂 MCP Resources (v0.3.0)

A single static Markdown reference is available at `khan://schema/main`
(MIME `text/markdown`). The agent reads this **on demand** when it
needs detailed technical info (storage layout, khal.conf format,
datetime semantics, error taxonomy, codebase map) without inflating
the per-turn prompt context.

```
ReadResourceResult(
    contents=[TextContent(
        uri="khan://schema/main",
        mime_type="text/markdown",
        text="..."  # ~150 lines of canonical reference
    )]
)
```

> **Why lazy?** `prompts/list` is content-injected; `resources/read`
> is lazy. Keeping the canonical reference out of the system prompt
> saves ~2k tokens per turn while still giving the LLM access when
> it asks for it.

---

## 🆕 Recent Improvements (post v0.2.0)

This release includes three rounds of bug fixes and feature work:

- **Auto-heal of drifted `khal.conf`** (`lifecycle._khal_conf_is_stale`):
  every boot compares the on-disk `khal.conf` against the rendered
  template (CRLF-normalised) and rewrites on divergence. Removes the
  silent-empty-`khan_list_events` failure mode after workspace migration.
- **S6 — canonical RFC-5545 `Z` form**: `DTSTART`/`DTEND` are now
  emitted as `YYYYMMDDTHHMMSSZ` on both create and update paths
  (was previously emitting `2026-07-23 12:30:00+00:00` after
  `khan_update_event`).
- **`constants.CONF_FILE` attribute access** in `subprocess_runner`
  so `monkeypatch`/runtime mutation propagates (was previously
  captured at module-import time).
- **Real-khal-CLI integration tests** (`pytest -m integration`):
  the previously-mocked `subprocess.run` is now exercised end-to-end
  against the real `khal 0.14.0` binary, catching layout drift
  before release.
- **Path-traversal guard** on the `calendar=` field
  (`KhalAdapter._validate_calendar_name`): rejects separators,
  leading dot, anything outside `[A-Za-z0-9_.-]{1,64}`.
- **Boot re-entrancy** (`server.main()`): each invocation constructs
  a fresh `FastMCP` instance instead of reusing the module-level
  global.

Coverage: **87.17%**. Tests: **181 unit + 2 integration**.

---

## 🐛 Bug History (Round-6 / Round-7)

Two production bugs were fixed and pinned with regression tests.

### `khan_list_events` returning empty despite existing events (Round 6)

Two-layer root cause:

1. **`lifecycle.setup_workspace`** only regenerated `khal.conf`
   when the file was **absent**. After the round-5 fix that moved
   the vdir `path` from `DATA_DIR` to `DATA_DIR/<calendar>`, existing
   workspaces kept the **stale** `khal.conf` pointing one level above
   where the adapter actually writes. Since `khal`'s vdir reader is
   non-recursive, every event written by the adapter was hidden
   from `khal list`.
2. **`subprocess_runner.executar_comando_khal`** imported
   `CONF_FILE` via `from ..constants import CONF_FILE` — a
   module-level binding captured at import time. Production
   monkeypatches / runtime mutations of `constants.CONF_FILE` were
   ignored.

Fix: `lifecycle._khal_conf_is_stale()` plus attribute-access read
of `constants.CONF_FILE` in `executar_comando_khal`. The full
investigation is captured in
`MCP_Docs/Issues/2026-07-22-percival-khan-calendar-list-events-mismatch.md`.

### `DTSTART:…+00:00` after `khan_update_event` (Round 6 / S6)

Cosmetic but real: after `khan_update_event` the on-disk .ics
re-serialised `DTSTART` and `DTEND` as `2026-07-23 12:30:00+00:00`
instead of the canonical RFC-5545 `20260723T123000Z` form. Both
are valid UTC datetimes, but the inconsistency broke interop with
calendar clients importing the exported `.ics`.

Root cause: `icalendar` v6's serializer choice depends on *which
method* was used to assign the property (`ev["x"] = value`
silently picks `+00:00`; `.add(UPPER, value)` picks `Z`). The
update path used subscript assignment.

Fix: `adapters/khal_adapter.py::_to_utc_z` normalises every
datetime to `tzinfo=timezone.utc` exactly, and the rebuild-Events
logic uses `.add(...)` exclusively. Regression test in
`tests/test_security_round6.py::TestDTStartSerializationCanonical`.

---

## ⚙️ Configuration in percival.OS (Nanobot)

Add the following configuration to your `~/.nanobot/config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "percival-khan-calendar": {
        "command": "percival-khan-calendar",
        "args": [],
        "env": {
          "PYTHONUNBUFFERED": "1",
          "KHAN_WORKSPACE_DIR": "/home/bill/.nanobot/workspace/khalCalendar",
          "KHAN_ENABLE_LOCK": "true",
          "KHAN_LOG_LEVEL": "INFO"
        },
        "toolTimeout": 60
      }
    }
  }
}
```

Alternatively, run from source:

```json
{
  "tools": {
    "mcpServers": {
      "percival-khan-calendar": {
        "command": "uv",
        "args": [
          "run",
          "--directory",
          "/path/to/percival-khan-calendar",
          "python",
          "-m",
          "percival_khan_calendar.server"
        ],
        "env": {
          "UV_PROJECT_ENVIRONMENT": "/path/to/shared/.venv",
          "PYTHONPATH": "/path/to/percival-khan-calendar/src"
        },
        "toolTimeout": 60
      }
    }
  }
}
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `KHAN_WORKSPACE_DIR` | `~/.nanobot/workspace/khalCalendar` | Where the calendar state lives. |
| `KHAN_DEFAULT_CALENDAR` | `nanobot` | Calendar name under `data/<calendar>/*.ics`. |
| `KHAN_ENABLE_LOCK` | `false` | If `true`, uses `fcntl.flock` on every write. |
| `KHAN_LOG_LEVEL` | `INFO` | Standard Python logging level. |

---

## 🛠️ Development & Testing

This project uses `uv` for dependency management.

```bash
# Sync environment (deps only)
uv sync

# Sync including optional test deps
uv sync --extra test

# Run unit tests (default; no khal binary required)
uv run pytest

# Run integration tests (requires khal binary + writable workspace)
uv run pytest -m integration

# Run with coverage
uv run pytest --cov=src/percival_khan_calendar --cov-report=term-missing
```

Lint and format:

```bash
uv run --with ruff ruff check .
uv run --with ruff ruff format .
```

---

## 📁 Layout (post v0.3.0)

```
src/percival_khan_calendar/
├── constants.py        # Final[Path] / Final[str] knobs
├── exceptions.py       # 4 typed exceptions
├── lifecycle.py        # setup_workspace + auto-heal
├── security.py         # envelope_untrusted_data + argument guard
├── server.py           # FastMCP entrypoint (fresh instance per boot)
├── models.py           # Pydantic validators
├── adapters/
│   ├── khal_adapter.py     # read/write + UID + canonical-Z serialiser
│   ├── locks.py            # workspace_lock context manager
│   └── subprocess_runner.py # executar_comando_khal + env passing
├── tools/
│   ├── create_event.py, delete_event.py, delete_event_safe.py
│   ├── export_ics.py, list_calendars.py, list_events.py
│   ├── search_events.py, status.py, update_event.py, view.py
│   └── prompts.py          # 6 primitive prompts (v0.3.0)
└── resources/
    └── docs.py             # khan://schema/main (v0.3.0)
```

---

## 📚 About the Project

This server is an integral module of the **percival.OS** project. It
acts as an agentic wrapper for `khal`, allowing Nanobot to manage your
schedule intelligently.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **Issues / Discussions**: [https://github.com/bill-kopp-ai-dev/percival.OS/issues](https://github.com/bill-kopp-ai-dev/percival.OS/issues)
- **License**: MIT
- **Issue tracker for this server**: `MCP_Docs/Issues/` in the
  upstream monorepo (e.g.
  `2026-07-22-percival-khan-calendar-list-events-mismatch.md`).

---

## 🩺 Troubleshooting

### `KhanInfrastructureError: khal binary not found`

Install khal:

```bash
# Option A: pip (works in any Python environment, including venv)
uv pip install khal

# Option B: apt (Debian / Ubuntu)
sudo apt install khal

# Verify
khal --version  # expect "0.14.0" or newer
```

### `KhanInfrastructureError: timed out after Xs`

The khal SQLite DB may be locked. Wait a moment and retry, or set
`KHAN_ENABLE_LOCK=false` if you have only one process touching the
calendar.

### `KhanAmbiguousMatchError: Ambiguous match for 'foo': N candidates`

Your search matched more than one event. Provide a more specific
term, or use `khan_get_event` to inspect candidates one by one.

### `KhanLockError: Workspace lock held by another process`

A second agent is currently editing the calendar. Wait a few
seconds, or set `KHAN_ENABLE_LOCK=false` (loses concurrency safety).

### `khan.conf` keeps re-generating on every boot

This is the **auto-heal** kicking in because something is mutating
the conf file (likely a side-effect of a tool that writes to it, or
external `khal` config edits). Look at the `khan_get_status` output
to see the drift message; the auto-heal is **safe and idempotent**.

### Workspace bootstrap failed

Make sure `~/.nanobot/workspace/khalCalendar` is writable. Delete
`khal.conf` to force regeneration on the next start. If permissions
keep getting denied, check umask and parent directory ownership.

### Running tests

```bash
uv sync --extra test
uv run pytest --cov=src/percival_khan_calendar --cov-report=term-missing
# 181 passed in ~5s; coverage 87.17%
```

---

## 📜 Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the full history. Current
release: **0.3.0** (documentation refresh + post-v0.2.0 fix
preservation).

---
*Developed with ❤️ by the percival.OS Team*
