# Stage-2 — Remediação do Percival Khan Calendar MCP

**Data / revisão:** 2026-10-27 / 1.0.  
**ID / estado:** S2-KC / execução local parcial; gates externos pendentes.
**Checkout executor:** `/home/bill/Projects/percival-khan-calendar`.  
**Responsável:** executor Khan a designar por bill; perfil/runtime com owner do gestor.

## 1. Objetivo e fontes

Tratar os 12 achados da **seção 6** do
[relatório Khan](../../../positronic-bean-IaC/docs/reports/2026-10-26-percival-khan-calendar-iac-readiness-report.md#6-achados-issues-e-inconsistências),
complementado pelas ações e revalidação das seções 7/9. São 12 ações: 2 P1,
3 P2 e 7 P3, sem P0. Baseline/HEAD na emissão:
`919b6ab9bb1b12d3ee48aa95c4d97f9463a738d0`. Exclusão local preexistente da
nota `docs/issues/2026-10-10-f3-status.md` preservada.

[Coordenador stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
— retorno S2-KC, seções 3 e 7; referências:
[consolidação](../../../positronic-bean-IaC/docs/reports/2026-10-26-stage-1-consolidated-readiness-report.md)
e [D-01..D-06](../../../positronic-bean-IaC/docs/decisions/2026-10-27-iac-stage-1-scope-and-pilot-decisions.md).

Emissão documental; execução futura neste projeto. Preservar 12 tools, 6 prompts,
resource e semântica RFC-5545, envelopes e path/argument guards. Conforme D-01,
Khan é segundo candidato para replicação, não substitui Notes no piloto inicial.
Operações de calendário usam somente workspace sintético; não migrar calendário
real automaticamente ao mudar o default de path.

## 2. Preparação e decisões

- [x] Ler instruções/README/config/CI disponíveis; baseline local `HEAD` é
  `69cce9061e24b88dedbf20e11df4c9993391083b`, worktree inicialmente limpo.
  Bill confirmou manter excluída a nota F3 `docs/issues/2026-10-10-f3-status.md`;
  não restaurada nem recriada.
- [x] Confirmar `khal` local e paths/defaults; `khal 0.14.0` responde no `.venv`.
  O novo default definido foi `${XDG_DATA_HOME:-~/.local/share}/percival/khan-calendar`;
  workspaces antigos requerem override explícito, sem migração automática. Build
  local e validações de fuso foram executados nesta rodada.
- [x] Corrigida a documentação desatualizada: `khal` está instalado das
  dependências Python travadas da imagem; sem bind ou instalação de binário host.
- [x] Decisões já registradas do owner: `KHAN_TIMEZONE=America/Sao_Paulo`
  configurável, lock default `true`, workspace novo fora da state_root e legado
  somente por override explícito. Perfil/lifecycle do broker ainda depende de S2-C01.
- [ ] Estimar por lote com bill (D-06). Ensaio de broker requer P0 Percival
  fechado e receita autorizada; plano operacional do piloto depende de D-05.

## 3. Backlog integral e critérios de aceite

Estado atualizado por ação registrado na execução de 2026-10-27, seção 6;
prioridades de origem preservadas.

| Ação | Achado / P | Trabalho e áreas previstas | Dependência / dono externo | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001 / P1 | Expor fuso/config e alinhar TZ em código, Dockerfile, Compose e perfil broker | Decisão do produto; S2-NB-X01 | Fixture de relógio em fronteira de dia: today/tomorrow, listagem e DTSTART coerentes com fuso configurado; host/container/perfil de install concordam; UTC e America/Sao_Paulo exercitados |
| A-002 | F-002 / P1 | Mover default do workspace para fora da state_root e documentar bind estreito com persistent true; manter migração explícita | S2-C01 e S2-NB-X01; política do broker vigente | Workspace sintético persiste após recriação, fora da raiz mascarada; sem bind de `/home` ou reabertura de path protegido; hipótese de runtime confirmada no broker |
| A-003 | F-003 / P2 | Corrigir docs/cabeçalho Dockerfile/AGENTS/PROJECT e instruções versionadas: khal é dependência embarcada | Revisar valores no candidato | Imagem informa khal presente e sua versão; 12 tools funcionam sem binário host; docs deixam de prescrever bind/instalação desnecessária |
| A-004 | F-004 / P2 | Combinar markers de integração/skipif e alinhar comandos README/AGENTS/PROJECT | Sem dependência externa | `pytest --no-cov -m integration` coleta os testes marcados e `-m "not integration"` os exclui; atualizar contagem se suíte evoluir, sem perder casos |
| A-005 | F-005 / P2 | Gerar candidato/scan vigente e decisão VEX; receber verificação do builder CI do gateway | S2-NB-X02; gate F3/etapa 2 IaC | Manifesto/SHA/DB/image ID, scan JSON e VEX por CVE quando aplicável; resultado CI do candidato, sem encerrar com banco antigo ou artefato inexistente |
| A-006 | F-006 / P3 | Unificar default KHAN_ENABLE_LOCK em código, imagem, Compose e docs | Decisão do owner; recomenda-se habilitado, não decisão já tomada | Mesmo default efetivo em todos; cenário de override explícito testado; A-012 usa lock habilitado |
| A-007 | F-007 / P3 | Atualizar badges, contagens, tag/HEAD, snapshot e estado conhecido do push | Somente evidência local ou consulta autorizada | Docs coerentes com SHA/suíte/tag; referência remote-tracking datada não apresentada como consulta remota atual |
| A-008 | F-008 / P3 | Registrar intenção de shutdown e/ou formalizar exit 143 esperado no contrato do gestor | S2-C01; S2-NB-X01 | SIGTERM observável, código documentado, escrita íntegra e lock liberado; aceitação de 143 não promete drain carregado |
| A-009 | F-009 / P3 | Produzir metadata/server.json aplicável e documento de instalação versionado, substituindo dependência de nota gitignored | S2-C03; etapas 2/4 IaC | Schema vigente validado, identidade/versão/imagem/transporte coerentes; instalação estreita e TZ explícitos, linkados ao manifesto |
| A-010 | F-010 / P3 | Fixar actions por SHA e verificar autenticação/origem do snapshot apt no build | Owner da cadeia de distribuição | Workflow pinado; evidência do mecanismo de verificação; `check-valid-until=no` não é prova suficiente de assinatura desativada; exceção só por decisão justificada com dono/prazo |
| A-011 | F-011 / P3 | Validar KHAN_SUBPROCESS_TIMEOUT na configuração com erro de operador controlado | Política de configuração do produto | Valor malformado falha controladamente sem traceback nem stdout poluído; não virar fallback silencioso sem decisão explícita |
| A-012 | F-012 / P3 | Adicionar prova real de dois processos escrevendo com lock habilitado em workspace sintético | A-006 | Dois escritores completam sem perda/corrupção do vdir/khal.db, dados/UID e locks íntegros; falha/crash libera lock conforme contrato |

A-010 precisa discriminar a afirmação sobre assinatura: expirar metadados e
autenticar pacotes são controles diferentes. Confirmar o build real antes de
atribuir bypass de assinatura; registrar conclusão corrigida com evidência nova.

## 4. Ordem dos lotes e retornos externos

1. **KC-1:** A-001/A-002/A-003, com regressões de fuso e path e plano de
   compatibilidade; A-004 corrige a seleção de integração.
2. **KC-2:** A-006→A-012, A-011/A-008/A-007. Manter escritas atômicas e guards;
   não habilitar dois escritores só porque o teste unitário de lock passou.
3. **KC-3:** A-005/A-009/A-010 com candidato/contrato do índice e CI. A-002
   recebe prova do broker pelo owner, após precondições, sem operar runtime real.

S2-NB-X01 cuida do perfil broker; S2-NB-X02 do gate de qualificação externo.
Mudanças externas não são executadas por este checkout. A etapa de replicação do
piloto exige documento próprio e evidência depois de D-05/D-06; publicação continua
nas etapas 2/4 do roadmap. Sem deadline/horas presumidos.

## 5. Qualificação futura no checkout

- [x] Regressões; `.venv/bin/pytest -q` passou com limiar >=80%; Ruff check/format
  check passaram. Seletores `--no-cov -m integration` e
  `--no-cov -m "not integration"` verificados.
- [x] Build local identificado como worktree dirty e protocolo MCP real stdio
  com `--network=none`; stdout JSON-RPC, initialize uma vez, `tools/list` (12)
  e chamada `khan_get_status` passaram. Fixture de fronteira UTC/Sao Paulo.
- [ ] Exercitar 12 tools com khal embarcado: create/list/update/export/delete
  **somente dados sintéticos**; nesta rodada apenas `khan_get_status` foi chamado
  pelo protocolo; operações completas das 12 tools ainda requerem smoke dedicado.
  Timeout inválido, concorrência e persistência sintética verificados.
- [ ] Repetir `V-BUILD`, `V-RUN`, `V-CONFIG`, `V-DATA`, `V-MCP`, `V-FUNC` afetados;
  `V-PILOT`/`V-REUSE` só com nova evidência específica, não pela escolha D-01.
- [ ] Receber aceites externos de path/perfil broker e scan/CI; documento de
  instalação versionado e rollback de path/estado antes de eventual operação real.

Mudança de default não autoriza mover calendário existente. Projeto com gate
externo pendente permanece parcial, mesmo com suíte local verde.

## 6. Penúltima etapa — documentar execução neste plano

- [x] Registrar por ação owner/data, SHA inicial/final, mudanças, comandos/ambiente,
  testes, evidências locais sanitizadas, `V-*` e dependências pendentes.
- [ ] Sincronizar o retorno na seção 3/7 do coordenador IaC após qualificação e
  aceite dos donos externos; manter baseline e não expor eventos reais.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / executor Khan | A-001/A-002/A-003/A-004/A-006 parciais; A-011 parcial; A-005/A-007/A-008/A-009/A-010/A-012 abertas | `3dc7e8a38333b07c7fe660871ff4b3c2ccb83602` → worktree não commitado | Bill decidiu `KHAN_TIMEZONE=America/Sao_Paulo` configurável, lock default `true`, workspace novo fora da state_root e legado só via override. Código/receitas alterados: timezone IANA, `TZ` no subprocesso, workspace XDG, markers de integração combinados, lock no Docker/Compose e parse do timeout finito >0. Evidência: `khal 0.14.0`; `231 passed`, cobertura 87.52%; dois testes integration passaram; selectors coletaram 2 integration e excluiram 2; Ruff check/format e `docker compose config --quiet` passaram. | Parcial. Sem build/candidato (`V-BUILD`), teste de fuso UTC/container cruzando dia, concorrência multiprocesso A-012 ou prova do broker A-002. A-005 aguarda scan vigente/VEX e CI gateway; A-007 ainda requer reconciliação de tag/HEAD sem alegar consulta remota; A-008 depende contrato S2-C01/owner broker; A-009 depende schema S2-C03; A-010 aguarda verificação da origem/autenticação apt e pinagem final. A-011 ainda precisa comprovar erro operador sem traceback/stdout poluído. `uv` CLI indisponível; testes/lint foram executados pelos bins do `.venv`. |
| 2026-10-27 / executor Khan | A-001 local; A-002 local; A-003/A-004/A-006/A-007/A-010/A-011/A-012 locais concluídas; A-005/A-008/A-009 e gates externos pendentes | `69cce9061e24b88dedbf20e11df4c9993391083b` → worktree não commitado (`GIT_SHA=69cce906-dirty` na imagem local) | Atualizados README, AGENTS/PROJECT, workflow CI e este plano. Nova entrada CLI converte timeout inválido em erro controlado; regressão adicionada. Testes: `234 passed`, cobertura 86.96%; quatro integration passaram (khal real, UTC/Sao Paulo na fronteira, 2 processos × 8 eventos, UIDs únicos, listagem real com 16 eventos, lock liberado inclusive após crash); 230 testes não-integration coletáveis. Ruff e Compose config passaram. `khal 0.14.0`; build local `percival-khan-calendar:stage2`, image ID `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`; MCP conformance em rede desativada (12 tools e status); volume sintético persistiu evento após recriação. Docker defaults `KHAN_ENABLE_LOCK=true`, `KHAN_TIMEZONE=America/Sao_Paulo`; override Compose `false` validado. APT: `apt-config` informa `AllowInsecureRepositories=0` e `AllowDowngradeToInsecureRepositories=0`; build de snapshot concluiu com `check-valid-until=no`, que afeta expiração e não desabilita verificação GPG. Actions fixadas a SHAs de releases upstream consultados. | Parcial (V-BUILD/V-RUN/V-CONFIG/V-DATA/V-MCP locais; qualificação integral não reivindicada). A-001 não cruzou fronteira em container/perfil do gestor; A-002 ainda aguarda prova do broker sem operar runtime real. A-005: Bill decidiu deixar scanner em aberto; Scout exigiu autenticação e não gerou SARIF; sem manifesto/scan/VEX nem CI gateway. A-008 aguarda contrato S2-C01. A-009 aguarda schema S2-C03. A-010 pinagem local aplicada e APT sem bypass de assinatura observado, mas falta validação no CI do gateway. A-007: tag local `v0.4.0` aponta `9fd14517e22be4c405eb8b6c0bb501a6770f2470`; HEAD local `69cce9061e24b88dedbf20e11df4c9993391083b`, igual ao remote-tracking local `origin/main` no início (não consultado remotamente); sem push efetuado. F3 permanece excluída por decisão do owner. Não atualizado projeto IaC/coordenador nesta execução. |

## 7. Última etapa — atualizar o plano coordenador

- [x] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md).
- [ ] Sincronizar **S2-KC na seção 3** e acrescentar retorno na **seção 7** após
  qualificação e aceites externos. Até lá, manter **aguardando sincronização**;
  conclusão exige aceites e retorno, e pendência/transferência não é problema resolvido.
