# Stage-2 — Remediação do Percival Khan Calendar MCP

**Data / revisão:** 2026-10-31 / 1.6.
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
  `R-07` exige VEX por CVE associado ao image ID e aprovado pelo owner, com CVEs
  da imagem base tratados por herança.
- [x] `R-11` — decisão de Bill em 2026-10-29, texto recebido: “Trivy instalado.
  Registre a decisão.” Trivy é o scanner escolhido para A-005; CLI instalado
  como pacote `0.76.1-1` e versão confirmada. Fluxo de execução: escanear TAR
  exportado do candidato limpo, sem montar o socket Docker; JSON será o
  relatório canônico, com scanner de vulnerabilidades e todas as severidades.
  Conforme R-17, OpenVEX JSON owner-approved será artefato separado do scan.
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
- [x] `R-17` — Bill decide adotar para Khan o padrão VEX usado nos planos
  Nanobot, IaC e OSM: OpenVEX em JSON, aprovado explicitamente pelo owner e
  limitado ao candidato/imagem e aos produtos/CVEs aplicáveis. A aprovação
  owner-approved não é assinatura criptográfica, waiver genérico, aprovação de
  release ou autorização de promoção. Cada candidato requer sua própria
  disposição; CVEs herdados da imagem base seguem a postura por herança. Trivy
  JSON continua sendo o relatório canônico do scan, separado do VEX.
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
| A-001 | F-001 / P1 | Expor fuso/config e alinhar TZ em código, Dockerfile, Compose e perfil broker | Parcial: implementação, regressão e configuração local; broker ainda não exercitado. Smoke pós-pin reportado passa, mas `khan_get_status` não expõe TZ/offset (lacuna de observabilidade baixa) | `R-12`; uma prova sintética no broker somente antes de adotar esse perfil | Reutilizar os testes locais de UTC/Sao_Paulo; na adoção do perfil, uma prova sintética confirma timezone e datas coerentes. Não repetir testes já cobertos pelo mesmo candidato |
| A-002 | F-002 / P1 | Mover default do workspace para fora da state_root e documentar bind estreito com `persistent: true`; manter migração explícita | Parcial: default novo, override legado, instrução de bind estreito e persistência sintética; perfil broker não exercitado | `R-12`; política `R-10`; agrupar com A-001/A-008 em uma prova se/quando o perfil for adotado | Confirmar uma vez em workspace sintético que o bind é estreito e os dados persistem após recriação; não alterar calendário real nem repetir prova já válida |
| A-003 | F-003 / P2 | Corrigir docs/cabeçalho Dockerfile/AGENTS/PROJECT e instruções versionadas: khal é dependência embarcada | Verificada localmente no candidato limpo de 2026-10-31: `khal 0.14.0`, `tools/list` (12 tools) e `khan_get_status` | Sem dependência de terceiros; evidência do build/smoke registrada em 2026-10-31 | No candidato limpo, confirmar `khal` embarcado, `tools/list` com as 12 tools e uma chamada de status; comportamento das tools é coberto pela suíte, sem repetir CRUD completo na imagem |
| A-004 | F-004 / P2 | Combinar markers de integração/skipif e alinhar comandos README/AGENTS/PROJECT | Verificada localmente: quatro integration selecionados e 230 testes excluídos | Sem dependência externa | `pytest --no-cov -m integration` coleta os testes marcados e `-m "not integration"` os exclui; atualizar contagem se suíte evoluir, sem perder casos |
| A-005 | F-005 / P2 | Gerar candidato/scan vigente e evidência VEX conforme o gate decidido | Verificada localmente em 2026-10-31: 12 CVEs no primeiro candidato; dependências corrigidas no lock; novo candidato escaneado com zero CVEs. Nenhum VEX necessário para o candidato final | `R-07`/`R-17`; scan canônico do TAR; Trivy JSON, manifest e SBOM ligados ao candidato por image ID e hashes | Vincular manifesto, SHA, DB, image ID e JSON do scan. Criar OpenVEX JSON owner-approved apenas para achados que exijam disposição; delimitar ao candidato/produto/CVE, sem alegar assinatura criptográfica ou promoção. CVEs herdados da base seguem a política registrada. Não considerar banco vencido ou evidência ausente como aceite |
| A-006 | F-006 / P3 | Unificar default KHAN_ENABLE_LOCK em código, imagem, Compose e docs | Verificada localmente: default `true` alinhado; override `false` validado | Decisão do owner registrada; teste multiprocesso A-012 | Mesmo default efetivo em todos; cenário de override explícito testado; A-012 usa lock habilitado |
| A-007 | F-007 / P3 | Atualizar badges, contagens, tag/HEAD, snapshot e estado conhecido do push | Parcial: badge coincide com 86,96%; pin local F2 conferido pela WebUI e inventory/audit; HEAD/tag locais verificados; remote não consultado, sem push | Somente evidência local ou consulta autorizada | Docs coerentes com SHA/suíte/tag; referência remote-tracking datada não apresentada como consulta remota atual |
| A-008 | F-008 / P3 | Documentar e comprovar o encerramento SIGTERM/143 | Parcial: evidência histórica [E-033](../../../positronic-bean-IaC/docs/reports/evidence/percival-khan-calendar/919b6ab9bb1b/khan_sigterm.py) registra SIGTERM/143; não comprova liberação de lock durante SIGTERM nem integridade de escrita nesse cenário | `R-12`; combinar com A-001/A-002 em uma prova sintética antes da adoção do perfil broker | Uma execução sintética registra saída 143 e integridade dos dados após stop, sem presumir drain. Reutilizar A-012 para liberação de lock após crash; só testar lock sob SIGTERM se houver escrita ativa que possa ser interrompida |
| A-009 | F-009 / P3 | Completar metadata `server.json` e extensão `pblabs.app.yaml` no índice local | Parcial: app manifest Khan passou validação do catálogo em 2026-10-31; `server.json` segue ausente e catálogo vazio. Índice continha alterações locais pré-existentes, preservadas | `R-06`, `R-14`; não criar referência de release sem digest de imagem publicada | Uma validação do metadata completo contra os schemas adotados; manter draft fora do catálogo instalável até haver imagem publicada com digest. Instruções de bind estreito e TZ ficam documentadas no mesmo perfil |
| A-010 | F-010 / P3 | Fixar actions por SHA e verificar autenticação/origem do snapshot apt no build | Parcial: actions pinadas e verificação local não indicou bypass de assinatura; CI gateway pendente | Decisão de Bill; evidência técnica no workflow/CI | Workflow pinado; evidência do mecanismo de verificação; `check-valid-until=no` não é prova suficiente de assinatura desativada; exceção só por decisão justificada com dono/prazo |
| A-011 | F-011 / P3 | Validar KHAN_SUBPROCESS_TIMEOUT na configuração com erro de operador controlado | Verificada localmente por teste de regressão: exit 2, stderr controlado, stdout vazio e sem traceback | Política de configuração do produto registrada | Valor malformado falha controladamente sem traceback nem stdout poluído; não virar fallback silencioso sem decisão explícita |
| A-012 | F-012 / P3 | Adicionar prova real de dois processos escrevendo com lock habilitado em workspace sintético | Verificada localmente: dois processos, 16 eventos únicos, listagem e liberação de lock após crash | A-006 verificada; workspace sintético | Dois escritores completam sem perda/corrupção do vdir/khal.db, dados/UID e locks íntegros; falha/crash libera lock conforme contrato |

A-010 discrimina expiração de metadados e autenticação de pacotes, que são
controles diferentes. Reutilizar a evidência do build; repetir a verificação
somente se a configuração de apt ou a imagem base mudar.

## 4. Ordem dos lotes e validações técnicas

1. **KC-1 — implementação local:** A-001 a A-004 estão implementadas e cobertas
   conforme a evidência local registrada. Não migrar calendário real.
2. **KC-2 — qualificação local:** A-006/A-011/A-012 foram verificadas; badge
   e cobertura foram reconciliados em 2026-10-31. A evidência local de SIGTERM
   não prova integridade de escrita nem liberação de lock nesse cenário.
3. **KC-3 — entregas técnicas restantes:** A-005 foi verificada no candidato
   local sem CVEs; A-009 ainda depende do metadata `server.json` apropriado a
   um release. A-010 requer validar o resultado no CI gateway, sem duplicar
   evidência local equivalente. Se/quando o perfil for adotado no broker, uma
   única prova sintética cobre A-001/A-002/A-008.

S2-NB-X01 e S2-NB-X02 identificam trabalho técnico no broker e gateway, não
owners ou aprovadores adicionais. Bill executa e decide. O perfil gerido só
precisa ser ensaiado antes de sua adoção; essa prova não bloqueia trabalho local.
O piloto de `R-13` só começa por decisão explícita de Bill. Não exigir a
demonstração multi-MCP `V-REUSE` de `R-15` como gate de Khan. `R-03` elimina
estimativas de esforço, custo ou prazo.

### 4.1. Harmonização com IaC — 2026-10-31

- A convenção de ownership `R-12` do coordenador IaC reafirma Bill como owner
  e decisor final; não cria aprovação duplicada nem altera a autorização
  necessária para operação real ou publicação. Ela não substitui a decisão
  local `R-12` deste plano sobre S2-C01.
- `R-10` é específico ao broker Percival: não amplia o bind estreito e
  persistente definido para Khan. A ADR C02 e o smoke DinD Percival+Notes também
  não comprovam o perfil Khan no broker; a prova sintética continua necessária
  somente antes de adotar esse perfil.
- O harness comum `pblabs-mcp-stdio/v1` está versionado e foi demonstrado em
  Notes e Weather. Conforme `R-15`, isso não é gate de Khan; tampouco substitui
  a validação do candidato Khan, a suíte, CI, testes funcionais ou transporte
  HTTP.
- A ação A-011 do plano IaC, sobre provenance do bundle, pertence ao bootstrap
  Percival, não ao Khan. Na harmonização inicial, A-005 ainda aguardava
  candidato/scan. A execução local abaixo agora registra candidato ligado ao
  SHA, lock e image ID; qualquer disposição por CVE continua específica à imagem.

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
- [x] Build limpo do código em SHA imutável e lockfile identificado no manifest;
  validar `--version`,
  `tools/list` (12 tools) e `khan_get_status`. Testar uma mutação na imagem
  somente se a mudança relevante não estiver coberta pela suíte automatizada,
  sempre em workspace sintético.
- [x] Atualizar a DB e escanear o TAR do candidato; guardar JSON,
  versão/data da DB, SHA do source e image ID. Criar OpenVEX JSON owner-approved
  somente para achados que precisem de disposição, com escopo explícito do
  candidato/produto/CVE; aprovação não é assinatura criptográfica nem promoção.
  O candidato final teve zero CVEs e não requereu VEX.
- [ ] Completar e validar o metadata de A-009. Antes de adotar o perfil broker,
  executar uma única prova sintética combinando timezone, bind/persistência e
  SIGTERM/143; registrar integridade dos dados. Reutilizar a evidência de A-012
  para liberação de lock após crash, sem repetir o teste em cada ação.
- [ ] Registrar somente os `V-*` afetados pelo candidato. `V-PILOT` é trabalho
  futuro, iniciado por Bill; `V-REUSE` não é gate deste plano.
- [x] Confirmar o badge de cobertura do README contra medição executada: ambos
  indicam 86,96%. Antes de qualquer operação real,
  confirmar o alvo e a integridade do workspace; nenhuma migração automática.

### Conferência do checkout — 2026-10-31

- O checkout atual está em `5b4698bf6a6693c7a22fec5239307930d1d84b48`;
  a árvore de trabalho contém alterações não commitadas neste plano. Portanto,
  os SHAs/imagem descritos nas entradas anteriores são fotografias históricas,
  não identificação do código atualmente qualificado.
- A coleta com `.venv/bin/pytest --no-cov --collect-only -q` encontrou 234
  testes: `-m integration` seleciona 4 e `-m "not integration"` seleciona
  230. Isso confirma a contagem/seletores de A-004, mas é coleta, não execução
  dos testes nem evidência nova de cobertura.
- `uv` não está disponível no PATH desta sessão; não foi possível reproduzir
  aqui os comandos históricos `uv run pytest`, Ruff ou Compose. As métricas de
  234 passes/86,54% permanecem evidência registrada em 2026-10-30, não foram
  revalidadas nesta revisão.
- A implementação inspecionada mantém `KHAN_TIMEZONE` validado como IANA,
  default `America/Sao_Paulo`; workspace XDG com override explícito; lock
  habilitado por default; validação de timeout finito e positivo; e auto-heal
  de `khal.conf`. A existência desses caminhos no código não comprova a prova
  de perfil/broker ainda pendente em A-001/A-002/A-008.
- Naquela conferência, o badge `86.96%` divergía da cobertura histórica
  `86,54%`. A execução local abaixo mediu novamente a suíte e resolve essa
  divergência para o checkout candidato.

### Execução local do plano — 2026-10-31

- `uv.lock` atualizado para corrigir os achados do primeiro scan: Authlib
  `1.7.2` → `1.9.1`, dnspython `2.8.0` → `2.9.1` e joserfc `1.7.4` → `1.7.7`.
  O primeiro candidato (image ID
  `sha256:bc7e18b0c8208b3a43790179f22c0721571491cbe0cc1cc33350a3faddbb86b2`)
  tinha 12 CVEs Python: 1 critical, 5 high, 5 medium e 1 low; Debian não
  reportou CVEs. Relatório integral:
  `/home/bill/.positronic/runtime/tmp/opencode/khan-stage2-5b4698b-trivy.json`.
- Após a atualização do lock, a suíte canônica passou: **234 passed**, cobertura
  **86,96%**. Ruff check e format check passaram. O badge README já indica
  `86.96%`, portanto não precisou de edição.
- Build sem cache `--pull --no-cache`, com fontes de aplicação do commit
  `5b4698bf6a6693c7a22fec5239307930d1d84b48` e `uv.lock` atualizado. Manifesto
  local: `/home/bill/.positronic/runtime/tmp/opencode/khan-stage2-5b4698b-build-manifest.json`;
  image ID `sha256:fccf598a6122d95e2a985ec7ad7d8e07b52c8c0e50ad3ec49ff08354b22e2524`;
  lock digest no manifesto `0db87115ad380699c5601ea3f0aeab8bb7e1d4efa10efe8f0fa31220f88c8a80`.
  Imagem `linux/amd64`, versão `0.4.0`, bases pinned e revision label igual
  ao commit. Evidências e TAR permanecem em `/home/bill/.positronic/runtime/tmp/opencode/`;
  nada foi publicado.
- O container respondeu `--version`; `khal --version` retornou `0.14.0`;
  conformance stdio offline passou com UID 1000, as 12 tools e chamada
  `khan_get_status` usando `/data` tmpfs sintético.
- TAR final SHA-256
  `375d8c3122f8d011cc847ea7a1ad921ce911bb811e4adcf4b3a74cdd40cbed78`;
  Trivy `0.76.1`, DB v2 (`UpdatedAt=2026-10-31 13:09 UTC`, `NextUpdate=2026-11-01
  13:09 UTC`), scan 2026-10-31 18:29 -03:00: **0 vulnerabilities** (Debian e
  Python). Não houve achados que demandassem disposição; portanto não foi criado
  VEX para esta imagem. JSON do scan:
  `/home/bill/.positronic/runtime/tmp/opencode/khan-stage2-5b4698b-r1-trivy.json`;
  SBOM CycloneDX SHA-256
  `8201bde64664c565f781b1f15a6f98e89252fb3e381380e57593bd033ff615cb`.
- `scripts/catalog.py --check`, executado usando o ambiente Khan por falta de
  `jsonschema` no venv do índice, passou: `catalog valid: 0 entries`. O app
  manifest Khan no índice está `manifest-approved`, mas `server.json` continua
  ausente; nenhuma alteração foi feita nesse outro checkout, que já tinha
  modificações locais alheias a esta execução.
- HEAD local permanece `5b4698bf6a6693c7a22fec5239307930d1d84b48`; tag local
  `v0.4.0` aponta para `9fd14517e22be4c405eb8b6c0bb501a6770f2470`. Nenhum remote
  foi consultado e nenhum push feito. A-001/A-002/A-008 do perfil broker só
  exigem prova sintética antes da adoção do perfil; piloto, publicação e
  promoção não foram iniciados.

### Pin local em Percival e limpeza — 2026-10-31

- Build canônico para consumo local pelo Percival, em worktree candidate F2:
  `percival-khan-calendar:0.4.0-5b4698b-f2-0c139187cd1e`; image ID
  `sha256:0c4d7b334fc5a1c949019ffa466489e352fc67a69132eb95c99739461afea49d`;
  source SHA `5b4698bf6a6693c7a22fec5239307930d1d84b48`, diff SHA
  `0c139187cd1eedf939f7cfde1b07825388dc9adb0f9e18416d56d68aba3ccac6`, `uv.lock`
  SHA-256 `31761ed82b63fd6bee2c318af48803d282459ddd75313ad228337afef0d70a20`.
  Build manifest produzido pelo script canônico; não é release nem publicação.
- A imagem foi executada offline em teste sintético: UID 1000, khal 0.14.0,
  initialize/tools/list (12) e `khan_get_status` passaram. Trivy 0.76.1/DB
  2026-10-31 reportou zero CVEs na imagem exata; sem necessidade de VEX.
  Evidência TAR/JSON em `/home/bill/.positronic/runtime/tmp/opencode/`.
- Bill realizou a pinagem no Percival WebUI e forneceu screenshots pós-operação:
  Docker state `running`, gateway intent `running`, MCP `connected` e 12 tools
  observadas no candidato. Inventário local confirma container
  `percival-mcp-khan-calendar` no ID `sha256:0c4d7b334fc5a1c949019ffa466489e352fc67a69132eb95c99739461afea49d`;
  configuração aponta ao mesmo ID, `active=true`, server revision 5 e global
  revision 28. Audit `update-image` foi `started` em revisão 27 e `committed` em
  28 com correlation ID `b88132f9a2f443f38364c274bfe1cc75`.
- Bill reporta, após o pin, leituras sem erro de `khan_get_status`,
  `khan_list_calendars`, `khan_view_agenda(period="today")`, `khan_list_events` e
  `khan_view_calendar`, sem mutação. Resultado reportado: layout `khal` coerente,
  lock habilitado, um calendário `nanobot`, zero eventos hoje e grade mensal vazia.
  TZ/offset não foi exposto — lacuna de observabilidade não bloqueante, sem
  evidência de falha de timezone. O relato declara “4 chamadas”, mas enumera cinco
  tools; a contagem exata de invocações é ambígua. Não foi reproduzido conteúdo de
  evento. O smoke direto pré-pin de `khan_get_status` também passou.
- Limpeza autorizada por Bill: removidos, após inventário read-only e confirmação
  de zero containers/config refs, os staging images sem referência
  `sha256:bc7e18b0c8208b3a43790179f22c0721571491cbe0cc1cc33350a3faddbb86b2` e
  `sha256:fccf598a6122d95e2a985ec7ad7d8e07b52c8c0e50ad3ec49ff08354b22e2524`;
  após a pinagem, removido também o pin A Percival antigo
  `sha256:55cd5a038d22e253693d1d0681e108f57b41f060ecbeb231dad3e2f7edd51914`.
  Consequência: rollback local para esse A requer rebuild, pois a imagem antiga
  não está arquivada. Mantido o pin Positronic
  `sha256:e67abbecf0be2c39da607a547dfdf67d0779b47e711b04f33598975ef85d6ac2` por
  estar ativo em outro gestor. Os três IDs removidos liberaram cerca de 389 MB
  de camadas únicas. `docker system df` final: 10.32 GB de imagens; o total
  cresceu em comparação à fotografia inicial devido ao gateway atualizado.

Mudança de default não autoriza mover calendário existente. Projeto com validação
de runtime/CI pendente permanece parcial, mesmo com suíte local verde. A cobertura
validada em 2026-10-31 coincide com o badge do README (`86.96%`).

## 6. Registro de execução neste plano

- [x] Registrar por ação owner/data, SHA inicial/final, mudanças, comandos/ambiente,
  testes, evidências locais sanitizadas, `V-*` e dependências pendentes.
- [x] Qualificação local repetida em 2026-10-30; resultados e limites ficam
  registrados abaixo, sem declarar runtime/CI externo como verificado.
- Atualizar o coordenador IaC apenas se uma decisão alterar dependência ou
  estado do roadmap. Essa cópia informativa não é pré-condição para executar ou
  concluir trabalho neste repositório.

As entradas abaixo são cronológicas. As decisões `R-11` a `R-17` estão
registradas nas linhas seguintes.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / executor Khan | A-001/A-002/A-003/A-004/A-006 parciais; A-011 parcial; A-005/A-007/A-008/A-009/A-010/A-012 abertas | `3dc7e8a38333b07c7fe660871ff4b3c2ccb83602` → worktree não commitado | Bill decidiu `KHAN_TIMEZONE=America/Sao_Paulo` configurável, lock default `true`, workspace novo fora da state_root e legado só via override. Código/receitas alterados: timezone IANA, `TZ` no subprocesso, workspace XDG, markers de integração combinados, lock no Docker/Compose e parse do timeout finito >0. Evidência: `khal 0.14.0`; `231 passed`, cobertura 87.52%; dois testes integration passaram; selectors coletaram 2 integration e excluiram 2; Ruff check/format e `docker compose config --quiet` passaram. | Parcial. Sem build/candidato (`V-BUILD`), teste de fuso UTC/container cruzando dia, concorrência multiprocesso A-012 ou prova do broker A-002. A-005 aguarda scan vigente/VEX e CI gateway; A-007 ainda requer reconciliação de tag/HEAD sem alegar consulta remota; A-008 depende contrato S2-C01/owner broker; A-009 depende schema S2-C03; A-010 aguarda verificação da origem/autenticação apt e pinagem final. A-011 ainda precisa comprovar erro operador sem traceback/stdout poluído. `uv` CLI indisponível; testes/lint foram executados pelos bins do `.venv`. |
| 2026-10-27 / executor Khan | A-001 local; A-002 local; A-003/A-004/A-006/A-007/A-010/A-011/A-012 locais concluídas; A-005/A-008/A-009 e gates externos pendentes | `69cce9061e24b88dedbf20e11df4c9993391083b` → worktree não commitado (`GIT_SHA=69cce906-dirty` na imagem local) | Atualizados README, AGENTS/PROJECT, workflow CI e este plano. Nova entrada CLI converte timeout inválido em erro controlado; regressão adicionada. Testes: `234 passed`, cobertura 86.96%; quatro integration passaram (khal real, UTC/Sao Paulo na fronteira, 2 processos × 8 eventos, UIDs únicos, listagem real com 16 eventos, lock liberado inclusive após crash); 230 testes não-integration coletáveis. Ruff e Compose config passaram. `khal 0.14.0`; build local `percival-khan-calendar:stage2`, image ID `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`; MCP conformance em rede desativada (12 tools e status); volume sintético persistiu evento após recriação. Docker defaults `KHAN_ENABLE_LOCK=true`, `KHAN_TIMEZONE=America/Sao_Paulo`; override Compose `false` validado. APT: `apt-config` informa `AllowInsecureRepositories=0` e `AllowDowngradeToInsecureRepositories=0`; build de snapshot concluiu com `check-valid-until=no`, que afeta expiração e não desabilita verificação GPG. Actions fixadas a SHAs de releases upstream consultados. | Parcial (V-BUILD/V-RUN/V-CONFIG/V-DATA/V-MCP locais; qualificação integral não reivindicada). A-001 não cruzou fronteira em container/perfil do gestor; A-002 ainda aguarda prova do broker sem operar runtime real. A-005: Bill decidiu deixar scanner em aberto; Scout exigiu autenticação e não gerou SARIF; sem manifesto/scan/VEX nem CI gateway. A-008 aguarda contrato S2-C01. A-009 aguarda schema S2-C03. A-010 pinagem local aplicada e APT sem bypass de assinatura observado, mas falta validação no CI do gateway. A-007: tag local `v0.4.0` aponta `9fd14517e22be4c405eb8b6c0bb501a6770f2470`; HEAD local `69cce9061e24b88dedbf20e11df4c9993391083b`, igual ao remote-tracking local `origin/main` no início (não consultado remotamente); sem push efetuado. F3 permanece excluída por decisão do owner. Não atualizado projeto IaC/coordenador nesta execução. |
| 2026-10-29 / executor Khan + Bill | 5/12 verificadas localmente (A-003/A-004/A-006/A-011/A-012); 5/12 parciais (A-001/A-002/A-005/A-008/A-010); 2/12 pendentes (A-007/A-009) | `3dc7e8a38333b07c7fe660871ff4b3c2ccb83602` → `3f4f6179b16760bef75193490768dffee8ec04e8`; qualificação começou com worktree limpo, antes desta revisão do plano. `main` três commits à frente da referência local `origin/main` (`6ae89b9`); remoto não consultado, sem push. `v0.4.0` → `9fd14517e22be4c405eb8b6c0bb501a6770f2470`. | `uv run pytest`: 234 passed, 86,54%; Ruff check/format, Compose config passaram. Seletores integration: 4 incluídos/230 excluídos. Regressões exercitam timezone UTC/Sao Paulo na fronteira, 2 processos × 8 eventos com UIDs únicos e liberação de lock após crash; timeout inválido gera exit 2, stderr controlado e stdout vazio. Ações CI pinadas por SHA. Badge README de coverage ainda marca 86,96%. Build local ainda é image ID `sha256:e02cd5d33ad9cd36873ed9af00d313e5517ab205b4131e7f4f70aa25c4cc0333`, com `GIT_SHA=69cce906-dirty`; sem rebuild limpo nem smoke de 12 tools no candidato atualizado. | Parcial. A-001 falta validação do perfil container/gestor; A-002 falta prova no broker. A-005 sem scanner escolhido, scan vigente, VEX assinado ou CI gateway. A-007 requer alinhar badge e sincronizar status sem alegar consulta remota. A-008 aguarda contrato S2-C01/broker. A-009 aguarda materializar/validar `server.json` e `pblabs.app.yaml` para `pblabs-mcp-index`. A-010 aguarda validação no CI gateway. Sem build limpo, piloto ou operação externa. | Retorno local qualificado; permanece parcial. Não libera runtime real, publicação nem etapas 2/4/5. Retorno ao coordenador ainda aguardando sincronização; gates externos continuam abertos. |
| 2026-10-29 / Bill | R-11: decisão registrada; A-005 scanner selecionado, execução ainda não realizada | `HEAD=3f4f6179b16760bef75193490768dffee8ec04e8`; worktree modificado somente por esta revisão documental | Texto recebido: “Trivy instalado. Registre a decisão.” `pacman -Qi trivy`: `0.76.1-1`; `trivy --version`: `0.76.1`. Vulnerability DB v2 indica atualização em 2026-10-28 07:10 UTC e `NextUpdate` 2026-10-29 07:10 UTC; executar refresh antes do scan. Fluxo definido: scanner de vulnerabilidades, todas as severidades, TAR do candidato limpo, JSON canônico; não montar socket Docker. | A-005 passa de scanner não escolhido para parcial. Sem build limpo, scan, VEX ou resultado CI; formato/mecanismo de assinatura do VEX aguarda escolha técnica de Bill, sem review de terceiros. Não atualizar nem publicar artefato real nesta etapa. |
| 2026-10-29 / Bill Kopp | R-12 a R-15: contrato S2-C01/C02 aceito para Khan; receita B de D-05 escolhida; destino C03 fixado; decisão de seguir o harness comum IaC fechada | Decisões registradas no plano Khan; sem alteração de código, broker, índice ou runtime | Bill é o único owner e decisor final de produto e IaC. Broker responsável pelo lifecycle; bind Khan estreito/persistente e timezone explícito; contrato requer registrar SIGTERM/143 e verificar integridade/lock, sem promessa de drain. DinD descartável com `--privileged` escolhido para futuro piloto. Destino local dos metadados: `/home/bill/Projects/pblabs-mcp-index`. Khan seguirá o harness comum indicado pelos planos IaC, sem implementação concorrente; esqueleto versionado e demonstração `V-REUSE` seguem como entregas técnicas. | Decisões fechadas, sem review/aceite de terceiros. Permanecem validações técnicas no broker/CI, materialização de metadados, versionamento/evidência do harness comum e futura execução do piloto; nada foi implantado ou executado nesta edição. |
| 2026-10-30 / Bill Kopp | R-16: confirma ownership/operação/decisão/assinatura exclusivos e reduz aprovações e provas repetidas; supera requisitos de processo redundantes de R-15 | `HEAD=18b517e` antes das edições documentais; código de aplicação inalterado | Suíte repetida: 234 passed, 86,54%; 4 testes de integração incluídos. Ruff, format, Compose config passaram. A imagem local ainda tem label `69cce906-dirty`; DB Trivy permanece vencida, sem novo scan. Índice local no commit `8fb9b95` contém draft `pblabs.app.yaml` para Khan, sem `server.json` e sem entrada no catálogo; validação do catálogo bloqueada por dependências ausentes. | A-008 não atribui ao teste histórico de SIGTERM liberação de lock ou integridade de escrita; A-009 reconhece o draft existente. Permanecem build/scan limpos e uma prova sintética no broker somente antes da adoção desse perfil. Nenhuma aprovação externa ou sincronização duplicada é gate. |
| 2026-10-31 / Bill | R-17: adota para Khan o padrão OpenVEX owner-approved dos planos Nanobot/IaC/OSM | Decisão documental; sem alteração de código, imagem ou runtime | Formato OpenVEX JSON; decisão explícita do owner; escopo por candidato/imagem, produto e CVE; Trivy JSON permanece relatório separado. VEX owner-approved não é assinatura criptográfica, waiver geral, aprovação de release ou promoção. CVEs da base tratados por herança. | A-005 não aguarda mais escolha de formato/mecanismo. A execução local e o scan do candidato estão registrados na entrada cronológica seguinte; só criar OpenVEX quando houver achados que exijam disposição. |
| 2026-10-31 / executor Khan | A-003/A-005 verificadas localmente; cobertura e badge reconciliados; A-009 app manifest validado, server.json pendente; A-010 local verificado | `HEAD=5b4698bf6a6693c7a22fec5239307930d1d84b48`; `uv.lock` alterado; imagem final `sha256:fccf598a6122d95e2a985ec7ad7d8e07b52c8c0e50ad3ec49ff08354b22e2524` | Primeiro scan: 12 CVEs Python (1 critical, 5 high, 5 medium, 1 low). Lock atualizado (Authlib 1.9.1, dnspython 2.9.1, joserfc 1.7.7); suíte 234 passed, 86,96%; Ruff check/format passaram. Rebuild sem cache; `--version`, `khal 0.14.0`, UID 1000, `tools/list` (12) e `khan_get_status` passaram em tmpfs sintético. Scan do TAR final, com DB Trivy atualizada: zero CVEs; sem VEX necessário. Manifest, JSON de scan, TAR e CycloneDX em runtime tmp; `catalog.py --check` passou com 0 entradas. Tag local v0.4.0 verificada; remote não consultado, sem push. | A-005 e smoke local de A-003 concluídos para o candidato local; não publicado. A-007 permanece parcial quanto a qualquer reconciliação remota. A-009 ainda sem server.json; índice externo não editado devido a alterações locais preexistentes. CI gateway não consultado; broker não alterado; perfil não adotado; V-PILOT não iniciado. |

## 7. Coordenador IaC (informativo)

O coordenador Stage-2 é um resumo, não uma aprovação ou dependência deste plano.
Atualizá-lo uma vez quando uma mudança local alterar uma dependência ou decisão
do roadmap; não bloquear trabalho local aguardando sincronização documental.

No início desta revisão, a linha S2-KC do [coordenador](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
ainda refletia o registro de 2026-10-27. Para Khan, R-16 substitui gates de
processo redundantes, como a demonstração multi-MCP de `V-REUSE`; isso não
bloqueia a execução local. Só atualizar o coordenador em uma passagem se Bill
decidir aplicar a simplificação também ao roadmap global.
