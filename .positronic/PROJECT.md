# Percival Khan Calendar

## Purpose and intended outcome

Manter e evoluir o servidor MCP `percival-khan-calendar` em producao: da ao
Nanobot capacidades autonomas, persistentes e seguras de gerenciar um
calendario local em cima da biblioteca `khal`, dentro do ecossistema
percival.OS (Personal Agentic Operating System). Sucesso = Nanobot operando
o calendario (criar / listar / buscar / atualizar / deletar eventos, agenda,
exportar `.ics`) sem regressao no contrato publico, com testes verdes e
hardening preservado.

## Scope and success criteria

Entregaveis:

1. **Contrato publico preservado** -- 12 tools + 6 prompts + 1 resource
   (`khan://schema/main`), com mesmos nomes e semantica. Qualquer mudanca de
   nome/schema e breaking change e exige coordenacao com o time do consumidor
   Nanobot antes de versionar.
2. **Suite de testes verde** -- `uv run pytest` com cobertura embutida
   >=80% (enforced em `[tool.pytest.ini_options].addopts`).
3. **Hardening mantido** -- prompt injection shields (XML envelopes em todo
   conteudo externo), argument guard (rejeita `-` / `--` em free-text inputs),
   path-traversal guard em `calendar=`, auto-heal de `khal.conf` drift,
   canonical RFC-5545 `Z` em `DTSTART`/`DTEND` em create/update.
4. **Lint/format limpos** -- `uv run --with ruff ruff check .` e
   `uv run --with ruff ruff format .`.
5. **Disciplina de bug-hunt** -- cada fix vem com regressao em `tests/`
   (precedente: rounds 2-8).

Evidencia de "funcionou": smoke contra o binario real `khal` (criar -> listar
-> buscar -> atualizar -> deletar, exportar `.ics`) **e** regressoes em
`tests/` para cada bug corrigido.

## Methods and resources

- Python >= 3.11, build via `hatchling` (`pyproject.toml`).
- Runtime: `mcp[cli] >= 1.12.0`, `fastmcp >= 3.2.0`, `khal >= 0.11.3`,
  `icalendar >= 6.0.0`. Venv + deps via `uv`.
- Testes: `pytest >= 8`, `pytest-cov >= 5`, `hypothesis >= 6`. Integracao
  opt-in via marker `integration` (requer binario `khal >= 0.14.0` +
  workspace gravavel).
- Lint/format: `ruff >= 0.11.2, < 1.0.0` (dev dep).
- Layout: `src/percival_khan_calendar/` (subpacotes por dominio:
  `adapters/`, `tools/`, `resources/`), `tests/`.
- Sem GPU; sem treino de modelo; CI `.github/`.

## Risks and governance

1. **Contrato publico.** Mudancas em tool name, schema ou semantica sao
   breaking -- coordenar com o time do consumidor Nanobot antes de
   versionar.
2. **Drift upstream.** `khal` / `icalendar` / FastMCP podem mudar
   comportamento (ex.: round-6 descobriu que `icalendar` v6 escolhe
   serializacao diferente entre `ev["x"] = value` e `.add(UPPER, value)`).
   Lockfile + CI + rounds de bug-hunt pass com regressao.
3. **Workspace lock contention.** `KHAN_ENABLE_LOCK` opcional; default
   `false` recomendado quando ha um unico processo.
4. **Modelo "calendario = dado nao-confiavel".** Todo conteudo externo lido
   do calendario e cercado por envelope XML e tratado como data, nunca como
   instrucao. Hardening preservado em mutacao.
5. **Path traversal.** `calendar=` validado em
   `KhalAdapter._validate_calendar_name` contra `[A-Za-z0-9_.-]{1,64}`
   antes do round-trip.
6. **Local-first / privacidade.** Calendario vive em
   `~/.nanobot/workspace/khalCalendar`; sync com nuvem so com consentimento
   explicito. Principio percival.OS.
7. **Licenca MIT** mantida; copyright `percival.OS Team`.

## Working conventions

- Lint/format: `uv run --with ruff ruff check .` e
  `uv run --with ruff ruff format .` (`line-length=100`, `target-version=py311`,
  regras `E,F,I,N,W`).
- Testes: `uv run pytest` (cobertura embutida >=80% enforced via
  `pyproject.toml`). Integracao opt-in: `uv run pytest -m integration`.
- Pre-commit: `.pre-commit-config.yaml`. CI em `.github/workflows/`.
- Cobertura report: `--cov-fail-under=80`, `show_missing=true`,
  `exclude_lines` documentadas em `pyproject.toml`.
- Manutencao corretiva: cada fix vem com regressao em `tests/` que falha
  sem o patch (precedente: rounds 2-8).
- Markdown table cells em `resources/docs.py` intencionalmente ignoram
  `E501`/`W605` (lidos por humanos, nao pelo lint layer).

## Verification

- Canonical: `uv run pytest` (com `--cov=src/percival_khan_calendar` +
  `--cov-fail-under=80` + `--cov-report=term-missing` ja embutidos em
  `[tool.pytest.ini_options].addopts`).
- Opcional: `uv run --with ruff ruff check .`,
  `uv run --with ruff ruff format --check .`, pre-commit.
- Live smoke (opt-in, fora do CI padrao): rodar o servidor contra uma
  instancia real do `khal`, validar `khan_get_status` + um
  create/list/delete ponta-a-ponta.

## Open questions

- **Release 0.4.0 (tagged 2026-09-26):** tag anotada `v0.4.0` em
  `699072b` (HEAD local). 4 commits granulares: `feat(server)`
  CLI `--version`/`--help`, `feat(docker)` Dockerfile/compose/CI,
  `docs(release)` notas + sync, `chore(release)` bump + lockfile.
  Contrato MCP preservado (12 tools + 6 prompts + 1 resource).
  Tudo verificado localmente: `uv run pytest` verde (220 passed /
  87.47%), `ruff check .` + `ruff format --check .` limpos,
  `docker build` + `docker run --version` + `docker inspect` + smoke
  via `docker compose run --rm server --version` verdes. Pendente:
  autorizacao para `git push origin main && git push origin v0.4.0`.
- **Docker empacotamento:** **entregue em v0.4.0**. Espelha o padrao
  `percival-agentmail-mcp` (multi-stage uv + python:3.12-slim, stdio
  MCP, OCI labels, UID 1000, env defaults via `:-`, sem `khal`
  binary bundled). CI job `docker` em `.github/workflows/ci.yml`
  reproduz os smokes localmente.
