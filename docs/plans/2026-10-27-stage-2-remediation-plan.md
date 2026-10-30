# Stage-2 — Remediação do Percival Khan Calendar MCP

**Data / revisão:** 2026-10-30 / 1.4.
**ID / estado:** S2-KC / execução local parcial; validações técnicas/runtime pendentes.
**Checkout executor:** `/home/bill/Projects/percival-khan-calendar`.  
**Owner, operador, decisor e signatário únicos:** Bill Kopp
(`bill.kopp.dev@gmail.com`), Positronic Bean Labs;
<https://labs.positronicbean.com>.
Bill é o único responsável pela aplicação e infraestrutura IaC e a única pessoa
que trabalha nesses projetos.

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

### Governança e verificações proporcionais

- Bill é o único owner, operador, decisor e signatário para aplicação, IaC,
  broker e publicação. Não exigir aprovações, reviews ou aceites de terceiros;
  registrar cada decisão uma vez e reaplicá-la ao escopo decidido.
- Validação técnica não é uma camada de aprovação. Para cada requisito, usar a
  evidência automatizada mais direta e suficiente; não repetir a mesma prova
  para o mesmo SHA/imagem nem exigir validações cruzadas entre planos/projetos.
- Executar a suíte canônica uma vez após mudanças relevantes. Rodar integração,
  smoke de container ou prova no broker apenas quando o requisito não estiver
  coberto por evidência válida existente ou quando a mudança afetar esse limite.
- Para operação gerida, agrupar timezone, bind/persistência e shutdown em uma
  única prova sintética quando todos forem relevantes. Não transformar esse
  ensaio em aprovação adicional ou pré-condição para trabalho local/documental.
- Registrar pendências como critérios técnicos concretos. Não criar gates de
  assinatura, sincronização documental, estimativa ou demonstração multi-MCP
  além do que Bill determinou ou do que um risco técnico real exigir.

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
  planos IaC se isso reduzir trabalho neste projeto, sem criar harness concorrente
  ou solicitar nova aprovação. Não exigir demonstração em dois MCPs nem esqueleto
  duplicado como gate de Khan; `V-REUSE` só é necessário se uma verificação
  concreta depender dele.
- [x] `R-16` — Bill confirma em 2026-10-30 que é o único owner, operador,
  decisor e signatário da aplicação e da IaC, e a única pessoa trabalhando
  nesses projetos. Não há aceite, review ou aprovação de terceiros. Reduzir
  validações redundantes: decisões ficam registradas uma vez; provas existentes
  são reutilizadas para o mesmo SHA/imagem; uma evidência suficiente por
  requisito basta. Manter somente testes que cubram comportamento alterado,
  limites reais de integração e salvaguardas necessárias. Este direcionamento
  substitui gates de processo anteriores que não detectem risco ou defeito
  técnico concreto.
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

Os 12 achados de origem permanecem rastreáveis, mas não criam camadas extras de
aprovação. A coluna de estado distingue implementação local de verificações
técnicas ainda necessárias; reutilizar uma evidência válida em vez de repeti-la.

| Ação | Achado / P | Trabalho e áreas previstas | Estado em 2026-10-30 | Decisão/base técnica | Aceite verificável |
|---|---|---|---|---|---|
| A-001 | F-001 / P1 | Expor fuso/config e alinhar TZ em código, Dockerfile, Compose e perfil broker | Parcial: implementação, regressão e configuração local; perfil broker ainda não exercitado | `R-12`; uma prova sintética no broker somente antes de adotar esse perfil | Reutilizar os testes locais de UTC/Sao_Paulo; na adoção do perfil, uma prova sintética confirma timezone e datas coerentes. Não repetir testes já cobertos pelo mesmo candidato |
| A-002 | F-002 / P1 | Mover default do workspace para fora da state_root e documentar bind estreito com `persistent: true`; manter migração explícita | Parcial: default novo, override legado, instrução de bind estreito e persistência sintética; perfil broker não exercitado | `R-12`; política `R-10`; agrupar com A-001/A-008 em uma prova se/quando o perfil for adotado | Confirmar uma vez em workspace sintético que o bind é estreito e os dados persistem após recriação; não alterar calendário real nem repetir prova já válida |
| A-003 | F-003 / P2 | Corrigir docs/cabeçalho Dockerfile/AGENTS/PROJECT e instruções versionadas: khal é dependência embarcada | Verificada localmente na documentação e dependências; candidato de imagem atual ainda não foi reconstruído | Sem dependência de terceiros; reutilizar o smoke de imagem de A-005 | No candidato limpo, confirmar `khal` embarcado, `tools/list` com as 12 tools e uma chamada de status; comportamento das tools é coberto pela suíte, sem repetir CRUD completo na imagem |
| A-004 | F-004 / P2 | Combinar markers de integração/skipif e alinhar comandos README/AGENTS/PROJECT | Verificada localmente: quatro integration selecionados e 230 testes excluídos | Sem dependência externa | `pytest --no-cov -m integration` coleta os testes marcados e `-m "not integration"` os exclui; atualizar contagem se suíte evoluir, sem perder casos |
| A-005 | F-005 / P2 | Gerar candidato/scan vigente e evidência VEX conforme o gate decidido | Parcial: Trivy escolhido; DB local vencida; build limpo, scan e VEX pendentes. A CI local gera manifesto/SBOM mas não executa Trivy | `R-07`; usar um scan canônico do TAR; consumir o resultado no gate existente quando aplicável, sem duplicar o scan | Vincular manifesto, SHA, DB, image ID e JSON do scan. Bill assina VEX somente para achados que exijam decisão de explorabilidade; CVEs herdados da base seguem a política registrada. Não considerar banco vencido ou evidência ausente como aceite |
| A-006 | F-006 / P3 | Unificar default KHAN_ENABLE_LOCK em código, imagem, Compose e docs | Verificada localmente: default `true` alinhado; override `false` validado | Decisão do owner registrada; teste multiprocesso A-012 | Mesmo default efetivo em todos; cenário de override explícito testado; A-012 usa lock habilitado |
| A-007 | F-007 / P3 | Atualizar badges, contagens, tag/HEAD, snapshot e estado conhecido do push | Parcial: este plano atualizado; badge README ainda informa 86,96% vs 86,54% medidos; sem consulta remota ou push | Somente evidência local ou consulta autorizada | Docs coerentes com SHA/suíte/tag; referência remote-tracking datada não apresentada como consulta remota atual |
| A-008 | F-008 / P3 | Documentar e comprovar o encerramento SIGTERM/143 | Parcial: evidência histórica [E-033](../../../positronic-bean-IaC/docs/reports/evidence/percival-khan-calendar/919b6ab9bb1b/khan_sigterm.py) registra SIGTERM/143; não comprova liberação de lock durante SIGTERM nem integridade de escrita nesse cenário | `R-12`; combinar com A-001/A-002 em uma prova sintética antes da adoção do perfil broker | Uma execução sintética registra saída 143 e integridade dos dados após stop, sem presumir drain. Reutilizar A-012 para liberação de lock após crash; só testar lock sob SIGTERM se houver escrita ativa que possa ser interrompida |
| A-009 | F-009 / P3 | Completar metadata `server.json` e extensão `pblabs.app.yaml` no índice local | Parcial: `pblabs.app.yaml` existe como draft; `server.json` ausente, catálogo vazio e validação do índice não concluída por dependências ausentes | `R-06`, `R-14`; completar apenas o necessário para o destino local | Uma validação do metadata completo contra os schemas adotados; manter draft fora do catálogo instalável até haver imagem publicada com digest. Instruções de bind estreito e TZ ficam documentadas no mesmo perfil |
| A-010 | F-010 / P3 | Fixar actions por SHA e verificar autenticação/origem do snapshot apt no build | Parcial: actions pinadas e verificação local não indicou bypass de assinatura; CI gateway pendente | Decisão de Bill; evidência técnica no workflow/CI | Workflow pinado; evidência do mecanismo de verificação; `check-valid-until=no` não é prova suficiente de assinatura desativada; exceção só por decisão justificada com dono/prazo |
| A-011 | F-011 / P3 | Validar KHAN_SUBPROCESS_TIMEOUT na configuração com erro de operador controlado | Verificada localmente por teste de regressão: exit 2, stderr controlado, stdout vazio e sem traceback | Política de configuração do produto registrada | Valor malformado falha controladamente sem traceback nem stdout poluído; não virar fallback silencioso sem decisão explícita |
| A-012 | F-012 / P3 | Adicionar prova real de dois processos escrevendo com lock habilitado em workspace sintético | Verificada localmente: dois processos, 16 eventos únicos, listagem e liberação de lock após crash | A-006 verificada; workspace sintético | Dois escritores completam sem perda/corrupção do vdir/khal.db, dados/UID e locks íntegros; falha/crash libera lock conforme contrato |

A-010 discrimina expiração de metadados e autenticação de pacotes, que são
controles diferentes. Reutilizar a evidência do build; repetir a verificação
somente se a configuração de apt ou a imagem base mudar.

## 4. Ordem dos lotes e validações técnicas

1. **KC-1 — implementação local:** A-001 a A-004 estão implementadas e cobertas
   conforme a evidência local registrada. Não migrar calendário real.
2. **KC-2 — qualificação local:** A-006/A-011/A-012 foram verificadas; A-007
   precisa apenas da atualização documental da cobertura. A evidência local de
   SIGTERM não prova integridade de escrita nem liberação de lock nesse cenário.
3. **KC-3 — entregas técnicas restantes:** A-005 requer um candidato limpo e um
   scan atual; A-009 requer completar/validar o draft de metadata. A-010 requer
   validar o comportamento do build, sem duplicar um resultado equivalente no
   gateway. Se/quando o perfil for adotado no broker, uma única prova sintética
   cobre A-001/A-002/A-008.

S2-NB-X01 e S2-NB-X02 identificam trabalho técnico no broker e gateway, não
owners ou aprovadores adicionais. Bill executa e decide. O perfil gerido só
precisa ser ensaiado antes de sua adoção; essa prova não bloqueia trabalho local.
O piloto de `R-13` só começa por decisão explícita de Bill. Não exigir a
demonstração multi-MCP `V-REUSE` de `R-15` como gate de Khan. `R-03` elimina
estimativas de esforço, custo ou prazo.

## 5. Qualificação local e gates

- [x] Em 2026-10-29 e repetido em 2026-10-30, `uv run pytest`: **234 passed**,
  cobertura **86,54%**
  (limiar 80%); `ruff check`, `ruff format --check` e
  `docker compose config --quiet` passaram.
- [x] Seletores: `uv run pytest --no-cov -m integration --collect-only -q`
  selecionou **4** testes; o seletor `not integration` selecionou **230**.
- [x] Quatro testes integration executam khal real em workspace temporário,
  incluindo timezone UTC/Sao Paulo em fronteira de dia e dois processos
  escritores (16 eventos, UIDs únicos, listagem e lock liberado após crash).
  O timeout inválido também tem regressão de erro CLI controlado.
- [x] A imagem MCP local continua anterior, com image ID
  `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`,
  mas o rótulo era `GIT_SHA=69cce906-dirty`; não é build limpo do HEAD
  atual e precisa ser substituído antes de qualificar essa imagem.
- [x] A evidência MCP desse build cobre stdio, `tools/list` (12) e chamada
  `khan_get_status`; a persistência sintética após recriação foi exercitada.
  Não repetir o smoke completo de mutações na imagem: a suíte cobre as tools;
  validar na imagem apenas descoberta das 12 tools e status, mais o caminho
  afetado se uma mudança específica exigir prova de integração.
- [x] Decisão `R-11`: Trivy `0.76.1-1` instalado e versão verificada. A base
  local informa `NextUpdate=2026-10-29 07:10 UTC`, portanto deve ser atualizada
  antes do scan; em 2026-10-30 a DB continua vencida. Não houve scan nem VEX.
- [x] O índice `/home/bill/Projects/pblabs-mcp-index` contém
  `servers/khan-calendar/pblabs.app.yaml` como draft no commit `8fb9b95`;
  `server.json` ainda não existe e o catálogo está vazio. `catalog.py --check`
  não pôde validar porque as dependências do índice não estão instaladas.
- [ ] Fazer um build limpo associado a SHA imutável; validar `--version`,
  `tools/list` (12 tools) e `khan_get_status`. Testar uma mutação na imagem
  somente se a mudança relevante não estiver coberta pela suíte automatizada,
  sempre em workspace sintético.
- [ ] Atualizar a DB e escanear uma vez o TAR do candidato; guardar JSON,
  versão/data da DB, SHA do source e image ID. Criar VEX somente para achados
  que precisem de decisão de explorabilidade; Bill assina o artefato final.
- [ ] Completar e validar o metadata de A-009. Antes de adotar o perfil broker,
  executar uma única prova sintética combinando timezone, bind/persistência e
  SIGTERM/143; registrar integridade dos dados. Reutilizar a evidência de A-012
  para liberação de lock após crash, sem repetir o teste em cada ação.
- [ ] Registrar somente os `V-*` afetados pelo candidato. `V-PILOT` é trabalho
  futuro, iniciado por Bill; `V-REUSE` não é gate deste plano.
- [ ] Atualizar o badge de cobertura do README. Antes de qualquer operação real,
  confirmar o alvo e a integridade do workspace; nenhuma migração automática.

Mudança de default não autoriza mover calendário existente. Projeto com validação
de runtime/CI pendente permanece parcial, mesmo com suíte local verde. O README ainda
mostra badge de cobertura `86.96%`, divergente dos `86.54%` medidos nesta revisão.

## 6. Registro de execução neste plano

- [x] Registrar por ação owner/data, SHA inicial/final, mudanças, comandos/ambiente,
  testes, evidências locais sanitizadas, `V-*` e dependências pendentes.
- [x] Qualificação local repetida em 2026-10-30; resultados e limites ficam
  registrados abaixo, sem declarar runtime/CI externo como verificado.
- Atualizar o coordenador IaC apenas se uma decisão alterar dependência ou
  estado do roadmap. Essa cópia informativa não é pré-condição para executar ou
  concluir trabalho neste repositório.

As entradas abaixo são cronológicas. As decisões `R-11` a `R-16` estão
registradas nas linhas seguintes.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / executor Khan | A-001/A-002/A-003/A-004/A-006 parciais; A-011 parcial; A-005/A-007/A-008/A-009/A-010/A-012 abertas | `3dc7e8a38333b07c7fe660871ff4b3c2ccb83602` → worktree não commitado | Bill decidiu `KHAN_TIMEZONE=America/Sao_Paulo` configurável, lock default `true`, workspace novo fora da state_root e legado só via override. Código/receitas alterados: timezone IANA, `TZ` no subprocesso, workspace XDG, markers de integração combinados, lock no Docker/Compose e parse do timeout finito >0. Evidência: `khal 0.14.0`; `231 passed`, cobertura 87.52%; dois testes integration passaram; selectors coletaram 2 integration e excluiram 2; Ruff check/format e `docker compose config --quiet` passaram. | Parcial. Sem build/candidato (`V-BUILD`), teste de fuso UTC/container cruzando dia, concorrência multiprocesso A-012 ou prova do broker A-002. A-005 aguarda scan vigente/VEX e CI gateway; A-007 ainda requer reconciliação de tag/HEAD sem alegar consulta remota; A-008 depende contrato S2-C01/owner broker; A-009 depende schema S2-C03; A-010 aguarda verificação da origem/autenticação apt e pinagem final. A-011 ainda precisa comprovar erro operador sem traceback/stdout poluído. `uv` CLI indisponível; testes/lint foram executados pelos bins do `.venv`. |
| 2026-10-27 / executor Khan | A-001 local; A-002 local; A-003/A-004/A-006/A-007/A-010/A-011/A-012 locais concluídas; A-005/A-008/A-009 e gates externos pendentes | `69cce9061e24b88dedbf20e11df4c9993391083b` → worktree não commitado (`GIT_SHA=69cce906-dirty` na imagem local) | Atualizados README, AGENTS/PROJECT, workflow CI e este plano. Nova entrada CLI converte timeout inválido em erro controlado; regressão adicionada. Testes: `234 passed`, cobertura 86.96%; quatro integration passaram (khal real, UTC/Sao Paulo na fronteira, 2 processos × 8 eventos, UIDs únicos, listagem real com 16 eventos, lock liberado inclusive após crash); 230 testes não-integration coletáveis. Ruff e Compose config passaram. `khal 0.14.0`; build local `percival-khan-calendar:stage2`, image ID `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`; MCP conformance em rede desativada (12 tools e status); volume sintético persistiu evento após recriação. Docker defaults `KHAN_ENABLE_LOCK=true`, `KHAN_TIMEZONE=America/Sao_Paulo`; override Compose `false` validado. APT: `apt-config` informa `AllowInsecureRepositories=0` e `AllowDowngradeToInsecureRepositories=0`; build de snapshot concluiu com `check-valid-until=no`, que afeta expiração e não desabilita verificação GPG. Actions fixadas a SHAs de releases upstream consultados. | Parcial (V-BUILD/V-RUN/V-CONFIG/V-DATA/V-MCP locais; qualificação integral não reivindicada). A-001 não cruzou fronteira em container/perfil do gestor; A-002 ainda aguarda prova do broker sem operar runtime real. A-005: Bill decidiu deixar scanner em aberto; Scout exigiu autenticação e não gerou SARIF; sem manifesto/scan/VEX nem CI gateway. A-008 aguarda contrato S2-C01. A-009 aguarda schema S2-C03. A-010 pinagem local aplicada e APT sem bypass de assinatura observado, mas falta validação no CI do gateway. A-007: tag local `v0.4.0` aponta `9fd14517e22be4c405eb8b6c0bb501a6770f2470`; HEAD local `69cce9061e24b88dedbf20e11df4c9993391083b`, igual ao remote-tracking local `origin/main` no início (não consultado remotamente); sem push efetuado. F3 permanece excluída por decisão do owner. Não atualizado projeto IaC/coordenador nesta execução. |
| 2026-10-29 / executor Khan + Bill | 5/12 verificadas localmente (A-003/A-004/A-006/A-011/A-012); 5/12 parciais (A-001/A-002/A-005/A-008/A-010); 2/12 pendentes (A-007/A-009) | `3dc7e8a38333b07c7fe660871ff4b3c2ccb83602` → `3f4f6179b16760bef75193490768dffee8ec04e8`; qualificação começou com worktree limpo, antes desta revisão do plano. `main` três commits à frente da referência local `origin/main` (`6ae89b9`); remoto não consultado, sem push. `v0.4.0` → `9fd14517e22be4c405eb8b6c0bb501a6770f2470`. | `uv run pytest`: 234 passed, 86,54%; Ruff check/format, Compose config passaram. Seletores integration: 4 incluídos/230 excluídos. Regressões exercitam timezone UTC/Sao Paulo na fronteira, 2 processos × 8 eventos com UIDs únicos e liberação de lock após crash; timeout inválido gera exit 2, stderr controlado e stdout vazio. Ações CI pinadas por SHA. Badge README de coverage ainda marca 86,96%. Build local ainda é image ID `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`, com `GIT_SHA=69cce906-dirty`; sem rebuild limpo nem smoke de 12 tools no candidato atualizado. | Parcial. A-001 falta validação do perfil container/gestor; A-002 falta prova no broker. A-005 sem scanner escolhido, scan vigente, VEX assinado ou CI gateway. A-007 requer alinhar badge e sincronizar status sem alegar consulta remota. A-008 aguarda contrato S2-C01/broker. A-009 aguarda materializar/validar `server.json` e `pblabs.app.yaml` para `pblabs-mcp-index`. A-010 aguarda validação no CI gateway. Sem build limpo, piloto ou operação externa. | Retorno local qualificado; permanece parcial. Não libera runtime real, publicação nem etapas 2/4/5. Retorno ao coordenador ainda aguardando sincronização; gates externos continuam abertos. |
| 2026-10-29 / Bill | R-11: decisão registrada; A-005 scanner selecionado, execução ainda não realizada | `HEAD=3f4f6179b16760bef75193490768dffee8ec04e8`; worktree modificado somente por esta revisão documental | Texto recebido: “Trivy instalado. Registre a decisão.” `pacman -Qi trivy`: `0.76.1-1`; `trivy --version`: `0.76.1`. Vulnerability DB v2 indica atualização em 2026-10-28 07:10 UTC e `NextUpdate` 2026-10-29 07:10 UTC; executar refresh antes do scan. Fluxo definido: scanner de vulnerabilidades, todas as severidades, TAR do candidato limpo, JSON canônico; não montar socket Docker. | A-005 passa de scanner não escolhido para parcial. Sem build limpo, scan, VEX ou resultado CI; formato/mecanismo de assinatura do VEX aguarda escolha técnica de Bill, sem review de terceiros. Não atualizar nem publicar artefato real nesta etapa. |
| 2026-10-29 / Bill Kopp | R-12 a R-15: contrato S2-C01/C02 aceito para Khan; receita B de D-05 escolhida; destino C03 fixado; decisão de seguir o harness comum IaC fechada | Decisões registradas no plano Khan; sem alteração de código, broker, índice ou runtime | Bill é o único owner e decisor final de produto e IaC. Broker responsável pelo lifecycle; bind Khan estreito/persistente e timezone explícito; contrato requer registrar SIGTERM/143 e verificar integridade/lock, sem promessa de drain. DinD descartável com `--privileged` escolhido para futuro piloto. Destino local dos metadados: `/home/bill/Projects/pblabs-mcp-index`. Khan seguirá o harness comum indicado pelos planos IaC, sem implementação concorrente; esqueleto versionado e demonstração `V-REUSE` seguem como entregas técnicas. | Decisões fechadas, sem review/aceite de terceiros. Permanecem validações técnicas no broker/CI, materialização de metadados, versionamento/evidência do harness comum e futura execução do piloto; nada foi implantado ou executado nesta edição. |
| 2026-10-30 / Bill Kopp | R-16: confirma ownership/operação/decisão/assinatura exclusivos e reduz aprovações e provas repetidas; supera requisitos de processo redundantes de R-15 | `HEAD=18b517e` antes das edições documentais; código de aplicação inalterado | Suíte repetida: 234 passed, 86,54%; 4 testes de integração incluídos. Ruff, format, Compose config passaram. A imagem local ainda tem label `69cce906-dirty`; DB Trivy permanece vencida, sem novo scan. Índice local no commit `8fb9b95` contém draft `pblabs.app.yaml` para Khan, sem `server.json` e sem entrada no catálogo; validação do catálogo bloqueada por dependências ausentes. | A-008 não atribui ao teste histórico de SIGTERM liberação de lock ou integridade de escrita; A-009 reconhece o draft existente. Permanecem build/scan limpos e uma prova sintética no broker somente antes da adoção desse perfil. Nenhuma aprovação externa ou sincronização duplicada é gate. |

## 7. Coordenador IaC (informativo)

O coordenador Stage-2 é um resumo, não uma aprovação ou dependência deste plano.
Atualizá-lo uma vez quando uma mudança local alterar uma dependência ou decisão
do roadmap; não bloquear trabalho local aguardando sincronização documental.

No início desta revisão, a linha S2-KC do [coordenador](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
ainda refletia o registro de 2026-10-27. Para Khan, R-16 substitui gates de
processo redundantes, como a demonstração multi-MCP de `V-REUSE`; isso não
bloqueia a execução local. Só atualizar o coordenador em uma passagem se Bill
decidir aplicar a simplificação também ao roadmap global.
