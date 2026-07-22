# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Refactor: roadmap published in `MCP_Docs/refactor_plans/percival-khan-calendar/`.

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
