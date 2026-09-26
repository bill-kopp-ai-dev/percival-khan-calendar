# AGENTS.md -- percival-khan-calendar

<!--
Project-scoped instructions for the `<positronic>` agent. Loaded into every
turn while this project is open. Extends (does not replace) the global
`AGENTS.md`, `SOUL.md` and `USER.md` loaded from `$POSITRONIC_HOME/`.

Owner: project-scoped operator. Edit directly with your editor; the runtime
re-reads on the next turn.
-->

## Project identity

- **Name:** `percival-khan-calendar`
- **Family:** percival.OS  **License:** MIT  **Upstream:**
  `bill-kopp-ai-dev/percival-khan-calendar`
- **Canonical brief:** `.positronic/PROJECT.md`

## Working conventions

- **Stack:** Python >=3.11, FastMCP >=3.2, `mcp[cli]` >=1.12,
  `khal` >=0.11.3, `icalendar` >=6.0. Venv + deps via `uv`
  (`uv sync` / `uv sync --extra test`).
- **Build:** `hatchling` (`pyproject.toml`).
- **Lint/format:** `uv run --with ruff ruff check .` e
  `uv run --with ruff ruff format .` (`line-length=100`, `py311`,
  regras `E,F,I,N,W`).
- **Manutencao corretiva:** cada fix vem com regressao em `tests/` que
  falha sem o patch (precedente: rounds 2-8).
- **Markdown table cells** em `resources/docs.py` ignoram `E501`/`W605`
  intencionalmente (lidos por humanos, nao pelo lint layer).
- Nao editar `.venv/`, `.git/`, `dist/`, `build/`, ou
  `.positronic/state.sqlite`.

## Verification

- **Canonical:** `uv run pytest` (cobertura embutida >=80% enforced via
  `[tool.pytest.ini_options].addopts`).
- **Lint isolado:** `uv run --with ruff ruff check .`.
- **Format check:** `uv run --with ruff ruff format --check .`.
- **Integracao opt-in:** `uv run pytest -m integration` (requer binario
  `khal >=0.14.0` + workspace gravavel em
  `~/.nanobot/workspace/khalCalendar`).
- **Pre-commit:** `uv run pre-commit run --all-files`.
- **Live smoke (opt-in):** rodar o servidor contra o binario `khal` real,
  validar `khan_get_status` + um create/list/delete ponta-a-ponta + export
  `.ics`. Requer workspace de teste configurado.

## MCP contract surface (v0.3.0)

- **Tools (12):** `khan_list_events`, `khan_search_events`, `khan_get_event`,
  `khan_view_agenda`, `khan_view_calendar`, `khan_list_calendars`,
  `khan_get_status`, `khan_create_event`, `khan_update_event`,
  `khan_delete_event`, `khan_delete_event_safe`, `khan_export_ics`.
- **Prompts (6):** `khan_overview`, `khan_create_event_semantics`,
  `khan_update_workflow`, `khan_delete_with_confirmation`,
  `khan_search_strategy`, `khan_quick_action_quick_create`.
- **Resource (1):** `khan://schema/main`.

Mudancas de nome/schema sao **breaking change** -- coordenar com o time
Nanobot antes de versionar.

## Security posture

- Conteudo lido do calendario e **dado nao-confiavel**; cercado por
  envelope XML antes de chegar ao LLM.
- Argument guard em free-text inputs rejeita `-` / `--`.
- Path-traversal guard em `calendar=` via
  `KhalAdapter._validate_calendar_name` (regex `[A-Za-z0-9_.-]{1,64}`).
- Auto-heal de `khal.conf` drift em `lifecycle._khal_conf_is_stale`.
- Canonical RFC-5545 `Z` form em `DTSTART`/`DTEND` em create/update
  (round-6 fix).

## Open questions

- **Versionamento pos round-9:** `pyproject.toml` ja bumpado para
  `0.4.0`; `CHANGELOG.md` e `README.md` atualizados; ainda sem tag
  Git. Decidir se a tag sai junto com o commit de release.
- **Refresh README:** badges atualizados em v0.4.0 para 220 tests /
  87.47% coverage; secao "🐳 Docker (v0.4.0)" nova.
- **Docker empacotamento:** **entregue em v0.4.0**. Multi-stage
  `Dockerfile` (uv 0.5.11 + python:3.12-slim, UID 1000, OCI labels,
  stdio MCP), `docker-compose.yml` local recipe, `.dockerignore`
  completo, e CI job `docker` (build + smoke `--version`/`--help` +
  inspect). `khal` binary nao bundleado por design (adapter-only
  tools funcionam; CLI-backed tools exigem `khal` no host PATH).

---

## Operator scratchpad (safe to delete)

Use esta secao para notas temporarias enquanto itera.
