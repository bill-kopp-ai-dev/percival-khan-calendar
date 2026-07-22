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
