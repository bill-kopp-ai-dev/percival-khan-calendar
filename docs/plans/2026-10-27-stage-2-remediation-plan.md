# Stage-2 — Remediação do Percival Khan Calendar MCP

**Data / revisão:** 2026-10-29 / 1.3.
**ID / estado:** S2-KC / execução local parcial; validações técnicas/runtime pendentes.
**Checkout executor:** `/home/bill/Projects/percival-khan-calendar`.  
**Owner único de produto e IaC:** Bill Kopp (`bill.kopp.dev@gmail.com`),
Positronic Bean Labs; <https://labs.positronicbean.com> (site em desenvolvimento).
Bill é o único responsável e decisor final da aplicação, servidores MCP e
infraestrutura IaC; execução técnica pode ser delegada sem transferir essa
autoridade.

## 1. Objetivo e fontes

Tratar os 12 achados da **seção 6** do
[relatório Khan](../../../positronic-bean-IaC/docs/reports/2026-10-26-percival-khan-calendar-iac-readiness-report.md#6-achados-issues-e-inconsistências),
complementado pelas ações e revalidação das seções 7/9. São 12 ações: 2 P1,
3 P2 e 7 P3, sem P0. O relatório de origem examina
`919b6ab9bb1b12d3ee48aa95c4d97f9463a738d0`; a execução local começou em
`3dc7e8a38333b07c7fe660871ff4b3c2ccb83602`. Exclusão local preexistente da
nota `docs/issues/2026-10-10-f3-status.md` preservada.

[Coordenador stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
— retorno S2-KC, seções 3 e 7; referências:
[consolidação](../../../positronic-bean-IaC/docs/reports/2026-10-26-stage-1-consolidated-readiness-report.md)
e [D-01..D-06](../../../positronic-bean-IaC/docs/decisions/2026-10-27-iac-stage-1-scope-and-pilot-decisions.md).

Este plano acompanha a execução local; esta revisão registra decisões, sem
executar mudanças em broker, publicação ou calendário real. Preservar 12 tools,
6 prompts, resource e semântica
RFC-5545, envelopes e path/argument guards. Conforme D-01, Khan é segundo
candidato para replicação, não substitui Notes no piloto inicial. Operações de
calendário usam somente workspace sintético; não migrar calendário real
automaticamente ao mudar o default de path.

## 2. Preparação e decisões

- [x] Preservar a nota F3 `docs/issues/2026-10-10-f3-status.md` excluída por
  decisão de Bill; não restaurada nem recriada.
- [x] Confirmar `khal` local e paths/defaults; `khal 0.14.0` responde no `.venv`.
  O novo default definido foi `${XDG_DATA_HOME:-~/.local/share}/percival/khan-calendar`;
  workspaces antigos requerem override explícito, sem migração automática. Build
  local e validações de fuso foram executados nesta rodada.
- [x] Corrigida a documentação desatualizada: `khal` está instalado das
  dependências Python travadas da imagem; sem bind ou instalação de binário host.
- [x] Decisões já registradas do owner: `KHAN_TIMEZONE=America/Sao_Paulo`
  configurável, lock default `true`, workspace novo fora da state_root e legado
  somente por override explícito. O contrato do perfil/lifecycle foi aceito em
  `R-12`; a validação do runtime broker continua pendente.
- [x] Atualização de decisão do operador em 2026-10-29: `R-10` supersede `R-02`
  quanto ao default do broker Percival, que permanece amplo conforme B14/B22/B23–B25.
  Khan deve configurar explicitamente o bind estreito do workspace persistente;
  não herdar o default amplo. Ampliar o perfil restrito exige decisão explícita
  de Bill e evidência técnica, sem revisão de terceiros.
  `R-03` remove a exigência de
  estimar esforço, custo ou prazo; `R-06` adota o schema externo de `server.json`,
  `pblabs.app.yaml` como extensão operacional e o índice `pblabs-mcp-index`,
  sem dependência do Docker MCP Catalog; `R-14` fixa o diretório local canônico.
  `R-07` exige VEX por CVE associado ao image ID e assinado pelo owner, com CVEs
  da imagem base tratados por herança.
- [x] `R-11` — decisão de Bill em 2026-10-29, texto recebido: “Trivy instalado.
  Registre a decisão.” Trivy é o scanner escolhido para A-005; CLI instalado
  como pacote `0.76.1-1` e versão confirmada. Fluxo de execução: escanear TAR
  exportado do candidato limpo, sem montar o socket Docker; JSON será o
  relatório canônico, com scanner de vulnerabilidades e todas as severidades.
  VEX permanece artefato separado; formato/mecanismo de assinatura aguardam
  escolha técnica de Bill, sem aprovação de terceiros.
- [x] Verificação de `trivy --version` em 2026-10-29 16:14 UTC: Vulnerability DB
  versão 2, `UpdatedAt=2026-10-28 07:10 UTC`, `NextUpdate=2026-10-29 07:10 UTC`;
  atualizar o DB antes do scan. Nenhum scan foi executado nesta decisão.
- [x] `R-12` — Bill aceita S2-C01 para Khan: o broker gerencia o lifecycle e a
  política de sinais; o perfil Khan usa bind estreito e persistente do workspace
  e timezone explícito. Registrar SIGTERM/exit 143 observado e verificar
  integridade dos dados e liberação do lock; o servidor não implementa drain e
  não deve ter essa capacidade presumida. S2-C02 (executor/transporte) está
  aprovado; falta comprovar implementação e adoção, não obter nova aprovação.
- [x] `R-13` — Bill escolhe a receita **(b) DinD descartável** para a futura prova
  vertical/piloto: DinD transitório com `--privileged`, em fixture/runner descartável.
  Esta escolha não inicia o piloto: execução e evidências continuam pendentes. O
  runner pode usar o daemon host para criar/remover o DinD; o socket/API host não
  será montado no broker/MCP sob teste, cuja API Docker ficará restrita à fixture.
  Usar apenas dados sintéticos, sem secrets ou mounts de produção, e registrar
  cleanup; `--privileged` é transitório e dá ao DinD privilégio elevado no host.
- [x] `R-14` — Bill define `/home/bill/Projects/pblabs-mcp-index` como destino
  local canônico dos metadados S2-C03. Mantêm-se o schema externo e a extensão
  operacional `pblabs.app.yaml` de `R-06`; o Docker MCP Catalog não é dependência.
- [x] `R-15` — Bill fecha a decisão de S2-C04: Khan seguirá o harness comum dos
  planos IaC, sem criar harness concorrente nem solicitar nova aprovação. Os
  planos definem as verificações comuns e o critério `V-REUSE`; a demonstração
  formal em pelo menos dois MCPs e o esqueleto versionado permanecem trabalho
  técnico. O coordenador IaC também lista documentar owner/localização/versão;
  tratar essa consolidação como rastreabilidade/entrega documental, não como
  decisão ou aceite de terceiros pendente (ver [plano detalhado](../../../positronic-bean-IaC/docs/plans/2026-10-26-iac-v1-stage-1-detailed-plan.md)
  e [coordenador Stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)).
- [x] O perfil de instalação documentado para Khan usa bind estreito explícito;
  não herda o default amplo do broker decidido por `R-10`.
- [ ] Prova desse perfil no broker e validação de runtime permanecem pendentes.
  A nota F3 continua excluída; o tracker canônico por imagem será mantido em
  `/home/bill/Projects/pblabs-mcp-index` (`R-05`/`R-14`), sem recriar cópia neste checkout.
- [x] Fotografia anterior à edição deste plano em 2026-10-29: `main` em
  `3f4f6179b16760bef75193490768dffee8ec04e8`, worktree limpo, três commits à
  frente da referência local `origin/main` (`6ae89b9207cdae4d98302388d5dbb7e50bbaa53c`).
  A referência remota não foi consultada e nenhum push foi feito. A tag local
  `v0.4.0` continua em `9fd14517e22be4c405eb8b6c0bb501a6770f2470`.

## 3. Backlog integral e critérios de aceite

As prioridades e os aceites de origem são preservados. A coluna de estado
distingue decisões já fechadas de validações técnicas pendentes; a fotografia detalhada e
datada está na seção 6.

| Ação | Achado / P | Trabalho e áreas previstas | Estado em 2026-10-29 | Decisão/base técnica | Aceite verificável |
|---|---|---|---|---|---|
| A-001 | F-001 / P1 | Expor fuso/config e alinhar TZ em código, Dockerfile, Compose e perfil broker | Parcial: implementação, regressão e configuração local; falta prova do perfil/container no broker | `R-12`; S2-NB-X01 (validação técnica) | Fixture de relógio em fronteira de dia: today/tomorrow, listagem e DTSTART coerentes com fuso configurado; host/container/perfil de install concordam; UTC e America/Sao_Paulo exercitados |
| A-002 | F-002 / P1 | Mover default do workspace para fora da state_root e documentar bind estreito com persistent true; manter migração explícita | Parcial: default novo, override legado, instrução de bind estreito e persistência sintética; broker não exercitado | `R-12`; S2-NB-X01 (validação técnica); política `R-10` | Workspace sintético persiste após recriação, fora da raiz mascarada; bind explicitamente estreito; não depender do default amplo do broker nem permitir acesso amplo implícito no perfil Khan; validar o comportamento no broker |
| A-003 | F-003 / P2 | Corrigir docs/cabeçalho Dockerfile/AGENTS/PROJECT e instruções versionadas: khal é dependência embarcada | Verificada localmente: documentação corrigida e `khal 0.14.0` presente no candidato local existente | Nenhuma externa; conferir no candidato limpo | Imagem informa khal presente e sua versão; 12 tools funcionam sem binário host; docs deixam de prescrever bind/instalação desnecessária |
| A-004 | F-004 / P2 | Combinar markers de integração/skipif e alinhar comandos README/AGENTS/PROJECT | Verificada localmente: quatro integration selecionados e 230 testes excluídos | Sem dependência externa | `pytest --no-cov -m integration` coleta os testes marcados e `-m "not integration"` os exclui; atualizar contagem se suíte evoluir, sem perder casos |
| A-005 | F-005 / P2 | Gerar candidato/scan vigente e evidência VEX conforme o gate decidido | Parcial: Trivy escolhido e CLI `0.76.1-1` instalado; DB local precisa atualização; candidato limpo, scan, VEX e CI ainda pendentes | S2-NB-X02 (execução técnica); `R-07`; etapa 2 IaC | Manifesto/SHA/DB/image ID, scan JSON e VEX por CVE detectado associado ao image ID e assinado pelo owner; CVEs da imagem base seguem a postura por herança; resultado CI do candidato, sem encerrar com banco antigo ou artefato inexistente |
| A-006 | F-006 / P3 | Unificar default KHAN_ENABLE_LOCK em código, imagem, Compose e docs | Verificada localmente: default `true` alinhado; override `false` validado | Decisão do owner registrada; teste multiprocesso A-012 | Mesmo default efetivo em todos; cenário de override explícito testado; A-012 usa lock habilitado |
| A-007 | F-007 / P3 | Atualizar badges, contagens, tag/HEAD, snapshot e estado conhecido do push | Parcial: este plano atualizado; badge README ainda informa 86,96% vs 86,54% medidos; sem consulta remota ou push | Somente evidência local ou consulta autorizada | Docs coerentes com SHA/suíte/tag; referência remote-tracking datada não apresentada como consulta remota atual |
| A-008 | F-008 / P3 | Documentar e provar o encerramento SIGTERM/143 no perfil broker | Parcial: SIGTERM/143 e liberação de lock observados localmente; falta validar perfil no broker e registrar integridade nessa execução | `R-12`; S2-NB-X01 (validação técnica) | SIGTERM observável, código documentado, escrita íntegra e lock liberado; aceitação de 143 não promete drain carregado |
| A-009 | F-009 / P3 | Produzir metadata `server.json` e extensão `pblabs.app.yaml` conforme `R-06`/`R-14`, mais instruções de instalação versionadas | Pendente: destino/schema decididos; manifest ainda não materializado nem validado | `R-06`, `R-14`; etapas 2/4 IaC | Schema externo adotado materializado/validado; identidade/versão/imagem/transporte coerentes; manifest destinado a `/home/bill/Projects/pblabs-mcp-index`; instalação estreita e TZ explícitos. Docker MCP Catalog não é dependência |
| A-010 | F-010 / P3 | Fixar actions por SHA e verificar autenticação/origem do snapshot apt no build | Parcial: actions pinadas e verificação local não indicou bypass de assinatura; CI gateway pendente | Decisão de Bill; evidência técnica no workflow/CI | Workflow pinado; evidência do mecanismo de verificação; `check-valid-until=no` não é prova suficiente de assinatura desativada; exceção só por decisão justificada com dono/prazo |
| A-011 | F-011 / P3 | Validar KHAN_SUBPROCESS_TIMEOUT na configuração com erro de operador controlado | Verificada localmente por teste de regressão: exit 2, stderr controlado, stdout vazio e sem traceback | Política de configuração do produto registrada | Valor malformado falha controladamente sem traceback nem stdout poluído; não virar fallback silencioso sem decisão explícita |
| A-012 | F-012 / P3 | Adicionar prova real de dois processos escrevendo com lock habilitado em workspace sintético | Verificada localmente: dois processos, 16 eventos únicos, listagem e liberação de lock após crash | A-006 verificada; workspace sintético | Dois escritores completam sem perda/corrupção do vdir/khal.db, dados/UID e locks íntegros; falha/crash libera lock conforme contrato |

A-010 precisa discriminar a afirmação sobre assinatura: expirar metadados e
autenticar pacotes são controles diferentes. Confirmar o build real antes de
atribuir bypass de assinatura; registrar conclusão corrigida com evidência nova.

## 4. Ordem dos lotes e validações técnicas

1. **KC-1 — implementação local concluída; aceites parciais:** A-001/A-002/A-003
   e A-004. Permanecem a prova do timezone no runtime gerido e a validação do
   perfil/mount estreito no broker; não migrar calendário real.
2. **KC-2 — qualificação local concluída em A-006/A-011/A-012; A-007/A-008
   parciais:** atualizar README e validar o contrato decidido em `R-12` no broker.
   Manter escritas atômicas e guards; limitar a concorrência comprovada ao
   workspace sintético.
3. **KC-3 — gates pendentes:** A-005/A-009 e validação CI de A-010. Para A-005,
   a escolha de scanner está fechada por `R-11`; faltam build limpo, refresh da
   DB, scan, VEX assinado e CI. A-002 recebe prova técnica do broker em fixture
   sintética, sem tocar runtime de produção ou calendário real. O critério VEX/schema/destino já está
   decidido em `R-06`/`R-07`; resta materializar e validar artefatos, não
   reabrir a escolha de política.

S2-NB-X01 identifica o trabalho técnico no perfil broker; Bill é o owner e
decisor também dessa infraestrutura. S2-NB-X02 identifica o gate de qualificação
do gateway. As decisões estão fechadas; as validações no broker/CI e a execução
futura do piloto continuam pendentes e não são realizadas por esta edição
documental. `R-13` seleciona a receita do piloto. Em `R-15`, o direcionamento
para Khan está decidido; resta o trabalho técnico de versionar/consolidar o
harness comum e evidenciar `V-REUSE`, sem criar implementação concorrente nem
aguardar aprovação. `R-03` remove estimativas de esforço, custo ou prazo.
Publicação continua nas etapas 2/4 do roadmap.

## 5. Qualificação local e gates

- [x] Em 2026-10-29, `uv run pytest`: **234 passed**, cobertura **86,54%**
  (limiar 80%); `ruff check`, `ruff format --check` e
  `docker compose config --quiet` passaram.
- [x] Seletores: `uv run pytest --no-cov -m integration --collect-only -q`
  selecionou **4** testes; o seletor `not integration` selecionou **230**.
- [x] Quatro testes integration executam khal real em workspace temporário,
  incluindo timezone UTC/Sao Paulo em fronteira de dia e dois processos
  escritores (16 eventos, UIDs únicos, listagem e lock liberado após crash).
  O timeout inválido também tem regressão de erro CLI controlado.
- [x] Há build MCP local anterior com image ID
  `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`,
  mas o rótulo era `GIT_SHA=69cce906-dirty`; não é build limpo do HEAD
  `3f4f617` e precisa ser substituído antes de qualificação final.
- [x] A evidência MCP desse build cobre stdio, `tools/list` (12) e chamada
  `khan_get_status`; a persistência sintética após recriação foi exercitada.
  O relatório de etapa 1 contém smoke de 12/12 tools em outro snapshot, não
  substitui smoke completo do candidato atual.
- [x] Decisão `R-11`: Trivy `0.76.1-1` instalado e versão verificada. A base
  local informa `NextUpdate=2026-10-29 07:10 UTC`, portanto deve ser atualizada
  antes do scan; não foi executado scan nem gerado VEX nesta etapa.
- [ ] Fazer build limpo associado a SHA imutável e repetir smoke stdio de 12
  tools, inclusive create/list/update/export/delete **somente em workspace
  sintético**; validar persistência no candidato limpo.
- [ ] Atualizar a Vulnerability DB do Trivy e escanear o TAR do candidato limpo;
  preservar JSON canônico, versão/data da DB, SHA do source e image ID. Gerar e
  assinar VEX em fluxo separado, após confirmar formato/chave do owner.
- [ ] Reconciliar `V-BUILD`, `V-RUN`, `V-CONFIG`, `V-DATA`, `V-MCP` e `V-FUNC`
  com o candidato limpo. `V-PILOT` exige a prova futura com a receita `R-13`;
  `V-REUSE` exige evidência do harness comum definido por `R-15`. Nenhum dos dois
  decorre apenas da decisão D-01.
- [ ] Executar validações técnicas do perfil/path no broker, scan/VEX no candidato
  limpo e gate CI; atualizar instruções de instalação e rollback antes de operação real.

Mudança de default não autoriza mover calendário existente. Projeto com validação
de runtime/CI pendente permanece parcial, mesmo com suíte local verde. O README ainda
mostra badge de cobertura `86.96%`, divergente dos `86.54%` medidos nesta revisão.

## 6. Penúltima etapa — documentar execução neste plano

- [x] Registrar por ação owner/data, SHA inicial/final, mudanças, comandos/ambiente,
  testes, evidências locais sanitizadas, `V-*` e dependências pendentes.
- [x] Qualificação local executada em 2026-10-29; esta revisão registra retorno
  parcial e evidências sem declarar validações de runtime/CI concluídas.
- [ ] Sincronizar as decisões e o retorno parcial nas seções 3/7 do coordenador
  IaC; registrar decisões sem aguardar validações e manter pendências técnicas
  abertas até haver evidência.

As entradas abaixo são cronológicas. O registro de qualificação em 2026-10-29
antecede `R-11`; as decisões `R-11` a `R-15` estão registradas nas linhas seguintes.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / executor Khan | A-001/A-002/A-003/A-004/A-006 parciais; A-011 parcial; A-005/A-007/A-008/A-009/A-010/A-012 abertas | `3dc7e8a38333b07c7fe660871ff4b3c2ccb83602` → worktree não commitado | Bill decidiu `KHAN_TIMEZONE=America/Sao_Paulo` configurável, lock default `true`, workspace novo fora da state_root e legado só via override. Código/receitas alterados: timezone IANA, `TZ` no subprocesso, workspace XDG, markers de integração combinados, lock no Docker/Compose e parse do timeout finito >0. Evidência: `khal 0.14.0`; `231 passed`, cobertura 87.52%; dois testes integration passaram; selectors coletaram 2 integration e excluiram 2; Ruff check/format e `docker compose config --quiet` passaram. | Parcial. Sem build/candidato (`V-BUILD`), teste de fuso UTC/container cruzando dia, concorrência multiprocesso A-012 ou prova do broker A-002. A-005 aguarda scan vigente/VEX e CI gateway; A-007 ainda requer reconciliação de tag/HEAD sem alegar consulta remota; A-008 depende contrato S2-C01/owner broker; A-009 depende schema S2-C03; A-010 aguarda verificação da origem/autenticação apt e pinagem final. A-011 ainda precisa comprovar erro operador sem traceback/stdout poluído. `uv` CLI indisponível; testes/lint foram executados pelos bins do `.venv`. |
| 2026-10-27 / executor Khan | A-001 local; A-002 local; A-003/A-004/A-006/A-007/A-010/A-011/A-012 locais concluídas; A-005/A-008/A-009 e gates externos pendentes | `69cce9061e24b88dedbf20e11df4c9993391083b` → worktree não commitado (`GIT_SHA=69cce906-dirty` na imagem local) | Atualizados README, AGENTS/PROJECT, workflow CI e este plano. Nova entrada CLI converte timeout inválido em erro controlado; regressão adicionada. Testes: `234 passed`, cobertura 86.96%; quatro integration passaram (khal real, UTC/Sao Paulo na fronteira, 2 processos × 8 eventos, UIDs únicos, listagem real com 16 eventos, lock liberado inclusive após crash); 230 testes não-integration coletáveis. Ruff e Compose config passaram. `khal 0.14.0`; build local `percival-khan-calendar:stage2`, image ID `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`; MCP conformance em rede desativada (12 tools e status); volume sintético persistiu evento após recriação. Docker defaults `KHAN_ENABLE_LOCK=true`, `KHAN_TIMEZONE=America/Sao_Paulo`; override Compose `false` validado. APT: `apt-config` informa `AllowInsecureRepositories=0` e `AllowDowngradeToInsecureRepositories=0`; build de snapshot concluiu com `check-valid-until=no`, que afeta expiração e não desabilita verificação GPG. Actions fixadas a SHAs de releases upstream consultados. | Parcial (V-BUILD/V-RUN/V-CONFIG/V-DATA/V-MCP locais; qualificação integral não reivindicada). A-001 não cruzou fronteira em container/perfil do gestor; A-002 ainda aguarda prova do broker sem operar runtime real. A-005: Bill decidiu deixar scanner em aberto; Scout exigiu autenticação e não gerou SARIF; sem manifesto/scan/VEX nem CI gateway. A-008 aguarda contrato S2-C01. A-009 aguarda schema S2-C03. A-010 pinagem local aplicada e APT sem bypass de assinatura observado, mas falta validação no CI do gateway. A-007: tag local `v0.4.0` aponta `9fd14517e22be4c405eb8b6c0bb501a6770f2470`; HEAD local `69cce9061e24b88dedbf20e11df4c9993391083b`, igual ao remote-tracking local `origin/main` no início (não consultado remotamente); sem push efetuado. F3 permanece excluída por decisão do owner. Não atualizado projeto IaC/coordenador nesta execução. |
| 2026-10-29 / executor Khan + Bill | 5/12 verificadas localmente (A-003/A-004/A-006/A-011/A-012); 5/12 parciais (A-001/A-002/A-005/A-008/A-010); 2/12 pendentes (A-007/A-009) | `3dc7e8a38333b07c7fe660871ff4b3c2ccb83602` → `3f4f6179b16760bef75193490768dffee8ec04e8`; qualificação começou com worktree limpo, antes desta revisão do plano. `main` três commits à frente da referência local `origin/main` (`6ae89b9`); remoto não consultado, sem push. `v0.4.0` → `9fd14517e22be4c405eb8b6c0bb501a6770f2470`. | `uv run pytest`: 234 passed, 86,54%; Ruff check/format, Compose config passaram. Seletores integration: 4 incluídos/230 excluídos. Regressões exercitam timezone UTC/Sao Paulo na fronteira, 2 processos × 8 eventos com UIDs únicos e liberação de lock após crash; timeout inválido gera exit 2, stderr controlado e stdout vazio. Ações CI pinadas por SHA. Badge README de coverage ainda marca 86,96%. Build local ainda é image ID `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`, com `GIT_SHA=69cce906-dirty`; sem rebuild limpo nem smoke de 12 tools no candidato atualizado. | Parcial. A-001 falta validação do perfil container/gestor; A-002 falta prova no broker. A-005 sem scanner escolhido, scan vigente, VEX assinado ou CI gateway. A-007 requer alinhar badge e sincronizar status sem alegar consulta remota. A-008 aguarda contrato S2-C01/broker. A-009 aguarda materializar/validar `server.json` e `pblabs.app.yaml` para `pblabs-mcp-index`. A-010 aguarda validação no CI gateway. Sem build limpo, piloto ou operação externa. | Retorno local qualificado; permanece parcial. Não libera runtime real, publicação nem etapas 2/4/5. Retorno ao coordenador ainda aguardando sincronização; gates externos continuam abertos. |
| 2026-10-29 / Bill | R-11: decisão registrada; A-005 scanner selecionado, execução ainda não realizada | `HEAD=3f4f6179b16760bef75193490768dffee8ec04e8`; worktree modificado somente por esta revisão documental | Texto recebido: “Trivy instalado. Registre a decisão.” `pacman -Qi trivy`: `0.76.1-1`; `trivy --version`: `0.76.1`. Vulnerability DB v2 indica atualização em 2026-10-28 07:10 UTC e `NextUpdate` 2026-10-29 07:10 UTC; executar refresh antes do scan. Fluxo definido: scanner de vulnerabilidades, todas as severidades, TAR do candidato limpo, JSON canônico; não montar socket Docker. | A-005 passa de scanner não escolhido para parcial. Sem build limpo, scan, VEX ou resultado CI; formato/mecanismo de assinatura do VEX aguarda escolha técnica de Bill, sem review de terceiros. Não atualizar nem publicar artefato real nesta etapa. |
| 2026-10-29 / Bill Kopp | R-12 a R-15: contrato S2-C01/C02 aceito para Khan; receita B de D-05 escolhida; destino C03 fixado; decisão de seguir o harness comum IaC fechada | Decisões registradas no plano Khan; sem alteração de código, broker, índice ou runtime | Bill é o único owner e decisor final de produto e IaC. Broker responsável pelo lifecycle; bind Khan estreito/persistente e timezone explícito; contrato requer registrar SIGTERM/143 e verificar integridade/lock, sem promessa de drain. DinD descartável com `--privileged` escolhido para futuro piloto. Destino local dos metadados: `/home/bill/Projects/pblabs-mcp-index`. Khan seguirá o harness comum indicado pelos planos IaC, sem implementação concorrente; esqueleto versionado e demonstração `V-REUSE` seguem como entregas técnicas. | Decisões fechadas, sem review/aceite de terceiros. Permanecem validações técnicas no broker/CI, materialização de metadados, versionamento/evidência do harness comum e futura execução do piloto; nada foi implantado ou executado nesta edição. |

## 7. Última etapa — atualizar o plano coordenador

- [x] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md).
- [ ] Sincronizar o retorno parcial: atualizar **S2-KC na seção 3** e acrescentar
  a entrada de 2026-10-29 na **seção 7** do coordenador IaC. Até a sincronização,
  manter **aguardando sincronização**; o registro parcial não fecha gates externos,
  e pendência/transferência não é problema resolvido.
