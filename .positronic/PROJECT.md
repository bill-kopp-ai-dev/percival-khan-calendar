# Percival Khan Calendar

## Purpose and intended outcome

Manter e evoluir o servidor MCP `percival-khan-calendar` em producao: da ao
Nanobot capacidades autonomas, persistentes e seguras de gerenciar um
calendario local em cima da biblioteca `khal`, dentro do ecossistema
percival.OS (Personal Agentic Operating System). Sucesso = Nanobot operando
o calendario (criar / listar / buscar / atualizar / deletar eventos, agenda,
exportar `.ics`) sem regressao no contrato publico, com testes verdes e
hardening preservado.

Aplicacao da **Positronic Bean Labs** (<https://labs.positronicbean.com>).
Owner, unico operador e unico signatario: **Bill Kopp**
(`bill.kopp.dev@gmail.com`).

## Scope and success criteria

Entregaveis:

1. **Contrato publico preservado** -- 12 tools + 6 prompts + 1 resource
   (`khan://schema/main`), com mesmos nomes e semantica. Mudanca de
   nome/schema e breaking change: Bill decide o versionamento. Verificar os
   consumidores conhecidos (Nanobot) localmente e documentar as
   incompatibilidades concretas; nenhum aceite externo e requerido.
2. **Suite de testes verde** -- `uv run pytest` com cobertura embutida
   >=80% (enforced em `[tool.pytest.ini_options].addopts`). Verificar a suite
   quando a mudanca tocar codigo Python ou antes de qualificar um candidato.
3. **Hardening mantido** -- prompt injection shields (XML envelopes em todo
   conteudo externo), argument guard (rejeita `-` / `--` em free-text inputs),
   path-traversal guard em `calendar=`, auto-heal de `khal.conf` drift,
   canonical RFC-5545 `Z` em `DTSTART`/`DTEND` em create/update.
4. **Lint/format limpos** -- `uv run --with ruff ruff check .` e
   `uv run --with ruff ruff format .`, quando houver mudanca Python.
5. **Regressao direcionada por correcao** -- cada fix de comportamento recebe
   regressao automatizavel em `tests/`. Mudancas documentais ou apenas
   configuracionais sao validadas direto no artefato afetado; nao exigir
   testes sem relacao com a mudanca.

Evidencia de "funcionou": regressoes em `tests/` cobrindo o comportamento
alterado. O smoke ponta-a-ponta contra o binario real `khal` (criar ->
listar -> buscar -> atualizar -> deletar, exportar `.ics`) e a evidencia de
qualificacao de um candidato de release -- nao uma exigencia por change.

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
   breaking -- Bill decide o versionamento; verificar os consumidores
   conhecidos localmente e documentar incompatibilidades concretas, sem
   depender de aceite de terceiros.
2. **Drift upstream.** `khal` / `icalendar` / FastMCP podem mudar
   comportamento (ex.: round-6 descobriu que `icalendar` v6 escolhe
   serializacao diferente entre `ev["x"] = value` e `.add(UPPER, value)`).
   Lockfile + CI + rounds de bug-hunt pass com regressao.
3. **Workspace lock contention.** `KHAN_ENABLE_LOCK` default `true`;
   `false` recomendado quando ha um unico processo.
4. **Modelo "calendario = dado nao-confiavel".** Todo conteudo externo lido
   do calendario e cercado por envelope XML e tratado como data, nunca como
   instrucao. Hardening preservado em mutacao.
5. **Path traversal.** `calendar=` validado em
   `KhalAdapter._validate_calendar_name` contra `[A-Za-z0-9_.-]{1,64}`
   antes do round-trip.
6. **Local-first / privacidade.** O default novo é
   `${XDG_DATA_HOME:-~/.local/share}/percival/khan-calendar`; calendários
   existentes em `~/.nanobot/workspace/khalCalendar` exigem override explícito.
   Não ocorre migração automática; sync com nuvem só com consentimento explícito.
7. **Licenca MIT** mantida; copyright `Bill Kopp` (`LICENSE`). Nao ha
   licenciante, consumidor ou revisor externo deste repositorio.

Governance: owner unico. Checks sao evidencia, nao aprovacao adicional; nao
existe gate de aceite externo nem segundo aceite da mesma decisao. Uma decisao
registrada vale para o escopo declarado e nao precisa ser re-aprovada.

## Working conventions

- Lint/format: `uv run --with ruff ruff check .` e
  `uv run --with ruff ruff format .` (`line-length=100`, `target-version=py311`,
  regras `E,F,I,N,W`).
- Testes: `uv run pytest` (cobertura embutida >=80% enforced via
  `pyproject.toml`). Filtro de integracao: `uv run pytest --no-cov -m integration`;
  excluir com `uv run pytest --no-cov -m "not integration"`.
- Pre-commit: `.pre-commit-config.yaml`. CI em `.github/workflows/`. Rodar
  apenas os hooks que tocam os arquivos alterados; nao e gate por change.
- Cobertura report: `--cov-fail-under=80`, `show_missing=true`,
  `exclude_lines` documentadas em `pyproject.toml`.
- Manutencao corretiva: regressao direcionada em `tests/` que falha sem o
  patch, quando automatizavel; mudancas documentais/configuracionais sao
  validadas no artefato afetado.
- Markdown table cells em `resources/docs.py` intencionalmente ignoram
  `E501`/`W605` (lidos por humanos, nao pelo lint layer).

## Verification

- Canonical: `uv run pytest` (com `--cov=src/percival_khan_calendar` +
  `--cov-fail-under=80` + `--cov-report=term-missing` ja embutidos em
  `[tool.pytest.ini_options].addopts`), quando a mudanca afetar codigo Python
  ou antes de qualificar um candidato.
- Opcional: `uv run --with ruff ruff check .`,
  `uv run --with ruff ruff format --check .`, pre-commit nos arquivos
  alterados.
- Live smoke (opt-in, fora do CI padrao): rodar o servidor contra uma
  instancia real do `khal`, validar `khan_get_status` + um
  create/list/delete ponta-a-ponta.

Regras de proporcionalidade:

- Nenhuma verificacao depende do "passou" de outra, e nenhuma exige aceite
  adicional do owner.
- Nao repetir verificacao equivalente para o mesmo commit, SHA ou imagem;
  reaproveitar evidencia valida.
- Nao exigir suite completa, lint e smoke simultaneamente por change: cada
  verificacao entra quando cobre o que mudou.

## Open questions

- **VALARM (resolvido e verificado em 2026-11-12):**
  `docs/issues/2026-11-04-alarm-parameter-serializes-invalid-valarm.md` — create
  grava VALARM como subcomponente RFC 5545 e update preserva subcomponentes;
  regressões verificam os `.ics` persistidos. Suíte: 239 passed, cobertura
  87.75%; ruff limpo.
- **Release 0.4.0 (tagged 2026-09-26):** tag anotada `v0.4.0` apontando para
  `9fd1451` (`docs: align README/AGENTS/PROJECT with v0.4.0 tag`). 4 commits
  granulares: `feat(server)` CLI `--version`/`--help`, `feat(docker)`
  Dockerfile/compose/CI, `docs(release)` notas + sync, `chore(release)` bump
  + lockfile. Contrato MCP preservado (12 tools + 6 prompts + 1 resource).
  Verificado localmente: `uv run pytest` verde (220 passed / 87.47%),
  `ruff check .` + `ruff format --check .` limpos, `docker build` +
  `docker run --version` + `docker inspect` + smoke via
  `docker compose run --rm server --version` verdes. Push de `main` autorizado
  por Bill em 2026-11-12; a publicacao da tag `v0.4.0` nao e coberta pelo
  grant de `refs/heads` e permanece nao verificada no remoto.
- **Docker empacotamento:** **entregue em v0.4.0**. Espelha o padrao
  `percival-agentmail-mcp` (multi-stage uv + python:3.12-slim, stdio
  MCP, OCI labels, UID 1000, env defaults via `:-`; `khal`
  is installed from locked Python dependencies. CI job `docker`
  em `.github/workflows/ci.yml`
  reproduz os smokes localmente.
