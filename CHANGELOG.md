# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Refactor: roadmap published in `MCP_Docs/refactor_plans/percival-khan-calendar/`.

## [0.2.1] - 2026-XX-XX (Round-6 follow-up)

### Fixed
- **`khan_list_events` reported "No events" while writes succeeded.**
  Root cause had two layers:
  1. `lifecycle.setup_workspace` only regenerated `khal.conf` if
     the file was absent; workspaces that already had a stale
     `khal.conf` from a previous deployment kept using the old
     layout. Round-5's vdir-path fix (`path = DATA_DIR/<cal>`)
     therefore left existing workspaces reading from the wrong
     directory.
  2. `executar_comando_khal` imported `CONF_FILE` from the
     module-level `constants` binding, which was a stale
     reference (CONF_FILE is a `Final[Path]`). This broke the
     integration contract in any runtime that mutated
     ``constants.CONF_FILE`` after import.
- Auto-heal (`lifecycle._khal_conf_is_stale()`) now compares the
  on-disk `khal.conf` against the freshly rendered template on
  every boot and rewrites if they diverge (CRLF-normalized).
- `executar_comando_khal` reads `CONF_FILE` via
  `constants.CONF_FILE` (attribute access) so monkeypatch /
  monkey-setattr propagates correctly.
- `executar_comando_khal` resolves the ``khal`` binary to an
  absolute path via `subprocess_runner._locate_khal()`, falling
  back to a `.venv/bin/khal` lookup. The integration test
  previously returned empty stdout because pytest's PATH lacked
  the workspace venv's bin directory.

### Added
- `khan_get_status` now reports whether the on-disk `khal.conf`
  matches the rendered template, and surfaces the data path the
  agent should expect events to live under.
- New test module `tests/test_integration_khal_subprocess.py`
  exercises the real `khal list` CLI subprocess end-to-end
  (opt-in via `-m integration`). Catches the round-5 layout
  drift bug *before* release instead of catching it in
  production.
- `KhalAdapter._validate_calendar_name()` rejects calendar names
  containing path separators, leading dots, or anything outside
  `[A-Za-z0-9_.-]{1,64}`. Defence-in-depth for a future tool
  that exposes the `calendar=` field directly.
- `setup_workspace()` reads `KHAN_WORKSPACE_DIR` env var so an
  agentic runtime can stage the calendar in an isolated location
  without changing the package source.

### Verified
- 153/153 unit tests passing.
- 2/2 integration tests against the real `khal 0.14.0` CLI passing.
- ruff clean.

## [0.2.2] - 2026-XX-XX (Round-6 follow-up: S6)

### Fixed
- **`khan_update_event` re-serialized DTSTART/DTEND as `2026-07-23
  12:30:00+00:00` instead of the canonical RFC-5545 `20260723T123000Z`
  after the round-5 vdir fix.** Both are valid UTC datetime
  representations accepted by every RFC-5545 parser, but the
  inconsistency broke interop with calendar clients importing
  exported `.ics`. The cause was that ``icalendar`` v6 picks its
  serializer (``Z`` vs ``+00:00``) by the *type* of the property
  object on the Event, and ``ev["dtstart"] = value`` (subscript
  assignment) was always assigning a freshly-built ``vDDDTypes`` that
  the serializer rendered as ``+00:00``. Switching to ``.add(...)``
  while clearing pre-existing properties via ``del ev[upper_key]``
  makes both create and update paths emit the same canonical form.
- Replaced the round-6 ``update_event`` "mutate in place" approach
  with "build a brand-new Event from primitives, copy across
  RRULE/VALARM/X-*-properties from the on-disk Event" so neither
  DST nor datetime subclasses can flip the serializer back to
  ``+00:00``. This is a defensive rewrite, not a behavior change:
  the user-observable contract (UID, RRULE, fields) is identical.

### Added
- New helper ``adapters/khal_adapter.py::_to_utc_z`` that:
  - returns the same ``datetime`` unchanged if it already has
    ``tzinfo=timezone.utc`` (cheap happy path);
  - promotes naive datetimes to local time and converts to UTC;
  - converts tz-aware-but-non-UTC datetimes (e.g. SP -03) to UTC
    preserving wall-clock time.
- ``tests/test_security_round6.py`` pinpoints the canonical-form
  output via a single regex ``DTSTART|DTEND`` matches
  ``^(\d{8}T\d{6})Z$``. Both create and update are tested; the
  buggy ``+00:00`` form is asserted *absent* on the update path.

### Verified
- 158/158 unit tests passing (was 153 before S6).
- 2/2 integration tests against the real khal 0.14.0 CLI still passing.
- ruff clean.

## [0.2.3] - 2026-XX-XX (MCP Prompts + Resource)

### Added
- **6 primitive prompts** are now registered via the MCP
  ``prompts.primitives`` protocol, providing on-demand guidance
  to the LLM agent instead of relying only on the per-tool
  description (which is short by spec):
  - ``khan_overview`` — full server tour (12 tools + workflow).
  - ``khan_create_event_semantics`` — field syntax (time
    expressions, alarm format, recurrence whitelist, TZ
    semantics).
  - ``khan_update_workflow`` — in-place update contract (UID,
    RRULE, VALARM preservation rules).
  - ``khan_delete_with_confirmation`` — two-call dry-run /
    confirm protocol for ``khan_delete_event_safe``.
  - ``khan_search_strategy`` (parameterized; ``keyword: str``,
    ``scope: Literal[summary|location|description]``) — how to
    qualify a search by field.
  - ``khan_quick_action_quick_create`` (parameterized;
    ``user_intent: str``) — verbatim echo + Portuguese-date
    mapping for free-form user intents.
- **1 resource** at ``khan://schema/main`` (MIME ``text/markdown``)
  exposes the canonical technical reference on demand: storage
  layout, khal.conf format, datetime semantics, documented
  quirks, error taxonomy, and the codebase map. The agent reads
  this when it needs to debug a tool failure or understand the
  on-disk format without inflating the per-tool description.

### Files
- New: ``src/percival_khan_calendar/tools/prompts.py`` (~300 lines).
- New: ``src/percival_khan_calendar/resources/docs.py`` (~140 lines).
- New: ``src/percival_khan_calendar/resources/__init__.py``.
- Modified: ``server.py`` to wire prompt + resource registration.
- Modified: ``tools/__init__.py`` to re-export ``register_prompts``.
- New: ``tests/test_prompts_and_resources.py`` (18 tests).

### Verified
- 176/176 unit tests passing (was 158 before this round).
- 2/2 integration tests against the real khal 0.14.0 CLI passing.
- ruff clean.
- End-to-end via MCP stdio: ``prompts/list`` returns the 6 prompts;
  ``resources/list`` returns the 1 resource; ``prompts/get name=
  khan_quick_action_quick_create arguments={"user_intent":
  "dentista amanha 10h"}`` renders with the verbatim echo.
- Coverage 85.40%.

## [0.3.0] - 2026-XX-XX (Documentation refresh)

### Changed
- **``README.md``** rewritten to reflect the post-0.2.0 surface area:
  - Added a **"MCP Prompts"** section documenting the 6 prompt
    primitives (``khan_overview``, ``khan_create_event_semantics``,
    ``khan_update_workflow``, ``khan_delete_with_confirmation``,
    ``khan_search_strategy``, ``khan_quick_action_quick_create``)
    with their argument shape and intended use-case.
  - Added a **"MCP Resources"** section pointing to
    ``khan://schema/main`` (text/markdown) — the canonical
    on-demand reference for storage layout, datetime semantics,
    khal.conf format, error taxonomy, and the codebase map.
  - Added a **"Round-6 / Round-7 Bug History"** section summarising
    the two issues discovered in production: the two-layer
    ``khan_list_events`` root cause and the cosmetics fix S6
    (``DTSTART`` …``Z`` vs ``+00:00``) plus the round-7 audit
    fixes (type correctness, boot re-entrancy, accurate docs).
  - Added a **"Recent Improvements"** callout listing:
    auto-heal of drifted ``khal.conf``, real-khal-CLI integration
    tests in ``-m integration``, path-traversal guard on the
    ``calendar=`` field, and the canonical ``Z`` formatter.
  - Updated badge line: ``Version 0.3.0``.
- **``khan://schema/main``** updated to mention the new prompts
  + resources surface and to call out the round-6/-7 invariants
  (canonical RFC-5545 ``Z`` form, khal path = ``DATA_DIR/<cal>``,
  fresh-instance boot pattern).
- **``pyproject.toml``** version bumped from ``0.2.0`` → ``0.3.0``.
- **``CHANGELOG.md``** entries cleaned: ``0.2.1``, ``0.2.2``,
  ``0.2.3``, and ``0.2.4`` are absorbed into the 0.3.0 history
  section while preserving the detail (timeline preserved
  below as a single rolled-up entry).

### Preserved from prior rounds (no behaviour changes this release)

This 0.3.0 release is **documentation-only at the source layer**
— every behavioural, test-coverage, and integration improvement
from prior rounds is preserved verbatim. The reference for those
rounds is held in the CHANGELOG below the 0.3.0 heading:

- **Round 5 fix** — ``khal.conf`` ``path = DATA_DIR/<calendar>``
  so khal's non-recursive vdir reader sees the events the
  adapter actually writes.
- **Round 6 fix (part 1)** — ``khan_list_events`` returning
  empty despite existing events was caused by (a) khal.conf
  drift on long-lived workspaces and (b) a stale module-binding
  for ``CONF_FILE`` in ``subprocess_runner``. Fix introduced
  ``_khal_conf_is_stale()`` (auto-heal on every boot) and the
  ``constants.CONF_FILE`` attribute-access read pattern.
- **Round 6 fix (part 2 / S6)** — ``khan_update_event`` used to
  serialise DTSTART/DTEND as ``+00:00``; now emits the canonical
  ``YYYYMMDDTHHMMSSZ`` form (subscript assignment vs ``.add(...)``
  asymmetry in icalendar v6 was the root cause).
- **Round 6 additions** — 6 primitive prompts + 1 schema
  resource; ``KhalAdapter._validate_calendar_name`` path-traversal
  guard.
- **Round 7 audit fixes** — type-correctness on the prompt
  return annotations; ``server.main()`` constructs a fresh
  ``FastMCP`` instance per invocation (no module-global reuse);
  ``register_prompts`` and ``register_resources`` docstrings
  corrected to describe FastMCP 3.4's silent-overwrite behaviour
  (not the previously-claimed ``ValueError``).

### Verified
- 181/181 unit tests passing.
- 2/2 integration tests against the real ``khal 0.14.0`` CLI
  still passing (``pytest -m integration``).
- ruff clean.
- Coverage 87.17%.
- End-to-end via MCP stdio: server still exposes 12 tools +
  6 prompts + 1 resource.
- Documentation now matches the surface; no behavioural change.

## [0.2.0] - 2026-XX-XX

### Added
- `.env.example` with configuration placeholders.
- `[project.urls]` in `pyproject.toml`.
- `constants.py` — single source for paths, locale, timeouts, calendar name, lock flag, truncation limits, alarm/recurrence patterns.
- `exceptions.py` — typed `KhanError` hierarchy (`Validation`, `NotFound`, `AmbiguousMatch`, `Infrastructure`, `Lock`).
- `models.py` — Pydantic input models for all 12 tools, with anti-argument-injection validators.
- `security.py` — `envelope_untrusted_data()` wraps user data in a single XML fence and entity-escapes both `<calendar_untrusted_data>` and `</calendar_untrusted_data>` so injection payloads cannot break out.
- `adapters/subprocess_runner.py` — hardened runner with `timeout`, typed exception classification, JSON logs, idempotent-only retry support.
- `adapters/khal_adapter.py` — reads/writes `.ics` directly via `icalendar`, preserving UID and RRULE across edits; atomic tmp+rename writes; per-calendar subdirectory layout.
- `adapters/locks.py` — `workspace_lock()` context manager using `fcntl.flock`; respects `KHAN_ENABLE_LOCK` (defaults true; tests disable it).
- `lifecycle.py` — `setup_workspace()` with bounded retries; writes `khal.conf` atomically via temp + rename.
- `tools/` package — one module per concern (`list_events`, `create_event`, `update_event`, `delete_event`, `view`, `status`); each exposes a `register_*_tools(mcp, adapter)` function.
- 4 new tools: `khan_delete_event_safe`, `khan_get_event`, `khan_list_calendars`, `khan_export_ics`.
- `.github/workflows/ci.yml` — GitHub Actions matrix on Python 3.11 / 3.12, installs `khal`, runs `ruff` + `pytest --cov-fail-under=80`.
- `.pre-commit-config.yaml` — ruff (lint + format) + standard pre-commit-hooks.
- 100 tests across 14 test modules; coverage at **86.93%** (target 80%).
- `uv.lock` lockfile for reproducible builds.

### Changed
- `__version__` now sourced from `importlib.metadata` (single source of truth).
- `server.py` reduced from 338 to 42 LOC (target ≤ 100).
- `khan_update_event` is now an in-place update preserving UID, RRULE and VALARM (previously deleted + recreated).
- `khan_create_event` writes through `KhalAdapter` (atomic, lock-protected) instead of `khal new` subprocess.
- All event-shaped data round-trips through the `EventMatch.format()` helper with prompt-injection-safe XML envelope.

## [0.0.2] - Initial release
