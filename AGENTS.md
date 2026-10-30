# AGENTS.md -- percival-khan-calendar

<!--
Project-scoped instructions for the `<positronic>` agent. Loaded into every
turn while this project is open. Extends (does not replace) the global
`AGENTS.md`, `SOUL.md` and `USER.md` loaded from `$POSITRONIC_HOME/`.

Owner: project-scoped operator. Edit directly with your editor; the runtime
re-reads on the next turn.
-->

## Owner and decisions

- **Owner, sole operator, decision-maker, and signer:** Bill Kopp
  (`bill.kopp.dev@gmail.com`), Positronic Bean Labs.
- **Website:** <https://labs.positronicbean.com>.
- Bill is the only person working on this application and its IaC. No third-party
  review, approval, or acceptance is required. Record each decision once and
  reuse it within its stated scope; do not create repeated approval gates.
- Technical checks are evidence, not additional approvals. Run only checks that
  address a concrete acceptance, compatibility, or safety requirement; reuse
  valid evidence for the same source/image instead of repeating it.
- Production changes, publication, and real-calendar mutations still require
  Bill's explicit instruction for that operation. This does not require a
  second approval after he has instructed it.

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
- **Correcoes de comportamento:** adicionar regressao direcionada quando
  automatizavel; para mudancas apenas documentais/configuracionais, validar
  diretamente o artefato afetado. Nao exigir testes sem relacao com a mudanca.
- **Markdown table cells** em `resources/docs.py` ignoram `E501`/`W605`
  intencionalmente (lidos por humanos, nao pelo lint layer).
- Nao editar `.venv/`, `.git/`, `dist/`, `build/`, ou
  `.positronic/state.sqlite`.

## Verification

- Escolher verificacoes que cubram o comportamento alterado; nao repetir
  validacoes equivalentes para o mesmo SHA/imagem.
- **Canonical:** `uv run pytest` (cobertura embutida >=80% enforced via
  `[tool.pytest.ini_options].addopts`), quando a mudanca afetar codigo Python
  ou antes de qualificar um candidato.
- **Lint/format:** `uv run --with ruff ruff check .` e
  `uv run --with ruff ruff format --check .` quando houver mudancas Python.
- **Integracao:** `uv run pytest --no-cov -m integration` (requer binario
  `khal >=0.14.0` + workspace gravavel), somente quando a mudanca afetar
  integracao com khal; excluir com
  `uv run pytest --no-cov -m "not integration"`.
- **Pre-commit:** `uv run pre-commit run --all-files`, quando hooks relevantes
  ou a qualificacao do candidato exigirem.
- **Container smoke:** validar versao, `tools/list` e uma leitura segura para
  candidato de imagem. Testar mutacoes ponta-a-ponta apenas quando forem
  afetadas pela mudanca, sempre em workspace sintetico.

## MCP contract surface (stable since v0.2.3; preserved verbatim in v0.4.0)

- **Tools (12):** `khan_list_events`, `khan_search_events`, `khan_get_event`,
  `khan_view_agenda`, `khan_view_calendar`, `khan_list_calendars`,
  `khan_get_status`, `khan_create_event`, `khan_update_event`,
  `khan_delete_event`, `khan_delete_event_safe`, `khan_export_ics`.
- **Prompts (6):** `khan_overview`, `khan_create_event_semantics`,
  `khan_update_workflow`, `khan_delete_with_confirmation`,
  `khan_search_strategy`, `khan_quick_action_quick_create`.
- **Resource (1):** `khan://schema/main`.

Mudancas de nome/schema sao **breaking change**. Bill decide quando versionar;
verifique consumidores conhecidos e documente incompatibilidades concretas,
sem exigir aceite de terceiros.

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

- **Baseline stage-2:** checkout revalidado em `3dc7e8a`; `khal 0.14.0`
  está instalado no ambiente e embarcado como dependência travada da imagem.
- **Docker empacotamento:** **entregue em v0.4.0**. Multi-stage
  `Dockerfile` (uv 0.5.11 + python:3.12-slim, UID 1000, OCI labels,
  stdio MCP), `docker-compose.yml` local recipe, `.dockerignore`
  completo, e CI job `docker` (build + smoke `--version`/`--help` +
  inspect). `khal` e as ferramentas CLI são instalados no virtualenv da imagem;
  não requerem binário nem bind do host.

---

## Operator scratchpad (safe to delete)

Use esta secao para notas temporarias enquanto itera.


## Docker MCP operations

- This MCP is stdio. Keep stdout JSON-RPC-only, without TTY, host port or HTTP
  healthcheck; its manager supplies the single init.
- The broker owns production container lifecycle; Compose is local development
  only. Use the supported interface and verify the target before a mutation;
  do not edit manager configuration or registry state by hand.
- Calendar mutations (create/update/delete) must use an isolated workspace in
  tests. Before an explicitly requested real-calendar operation, verify
  `khan_get_status` or another safe read. Do not expose calendar data or secrets.
