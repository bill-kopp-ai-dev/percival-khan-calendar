# Stage-2 — Remediação do Percival Khan Calendar MCP

**Data / revisão:** 2026-10-27 / 1.0.  
**ID / estado:** S2-KC / planejado; execução não iniciada.  
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

- [ ] Ler instruções/README/config/CI disponíveis; registrar SHA/worktree e
  reconciliar com o owner o destino da nota F3 localmente excluída.
- [ ] Confirmar `khal` da imagem, paths/defaults e timezone. A documentação antiga
  em `AGENTS.md`/PROJECT sobre ausência do `khal` é parte do achado, não prova atual.
- [ ] Owner decide knob de fuso, default do lock e estratégia de compatibilidade
  para workspace antigo; S2-C01 define perfil e lifecycle com o broker.
- [ ] Estimar por lote com bill (D-06). Ensaio de broker requer P0 Percival
  fechado e receita autorizada; plano operacional do piloto depende de D-05.

## 3. Backlog integral e critérios de aceite

Todas as ações **não iniciadas**. Prioridades das ações de origem preservadas.

| Ação | Achado / P | Trabalho e áreas previstas | Dependência / dono externo | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001 / P1 | Expor fuso/config e alinhar TZ em código, Dockerfile, Compose e perfil broker | Decisão do produto; S2-NB-X01 | Fixture de relógio em fronteira de dia: today/tomorrow, listagem e DTSTART coerentes com fuso configurado; host/container/perfil de install concordam; UTC e America/Sao_Paulo exercitados |
| A-002 | F-002 / P1 | Mover default do workspace para fora da state_root e documentar bind estreito com persistent true; manter migração explícita | S2-C01 e S2-NB-X01; política do broker vigente | Workspace sintético persiste após recriação, fora da raiz mascarada; sem bind de `/home` ou reabertura de path protegido; hipótese de runtime confirmada no broker |
| A-003 | F-003 / P2 | Corrigir docs/cabeçalho Dockerfile/AGENTS/PROJECT e instruções versionadas: khal é dependência embarcada | Revisar valores no candidato | Imagem informa khal presente e sua versão; 12 tools funcionam sem binário host; docs deixam de prescrever bind/instalação desnecessária |
| A-004 | F-004 / P2 | Combinar markers de integração/skipif e alinhar comandos README/AGENTS/PROJECT | Sem dependência externa | `pytest -m integration` coleta os 2 testes atuais e `-m "not integration"` os exclui; atualizar contagem se suíte evoluir, sem perder casos |
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

- [ ] Regressões para cada fix observado; `uv run pytest` com limiar vigente >=80%,
  lint/format check conforme CI. Exercitar seleção integration/not integration.
- [ ] Build identificado e protocolo MCP real em stdio sem rede; stdout só JSON-RPC,
  init único do gestor, fixtures de data/hora/workspace.
- [ ] Exercitar 12 tools com khal embarcado: create/list/update/export/delete
  **somente dados sintéticos**; TZ, timeout inválido, concorrência e persistência.
- [ ] Repetir `V-BUILD`, `V-RUN`, `V-CONFIG`, `V-DATA`, `V-MCP`, `V-FUNC` afetados;
  `V-PILOT`/`V-REUSE` só com nova evidência específica, não pela escolha D-01.
- [ ] Receber aceites externos de path/perfil broker e scan/CI; documento de
  instalação versionado e rollback de path/estado antes de eventual operação real.

Mudança de default não autoriza mover calendário existente. Projeto com gate
externo pendente permanece parcial, mesmo com suíte local verde.

## 6. Penúltima etapa — documentar execução neste plano

- [ ] Registrar por ação owner/data, SHA inicial/final, mudanças, comandos/ambiente,
  testes, evidências locais sanitizadas, `V-*` e dependências pendentes.
- [ ] Reconciliar docs atuais; acrescentar revalidação à seção 9 do relatório IaC
  quando autorizado, preservando baseline e sem expor eventos reais.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| Pendente | A-001–A-012 | A registrar | Nenhuma execução nesta emissão | Não iniciada |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md),
  atualizar **S2-KC na seção 3** e acrescentar retorno na **seção 7**, com ações
  verificadas/abertas, SHA/evidências, aceites externos e dependências liberadas.
- [ ] Preservar retornos alheios, indicar efeito sobre replicação e etapas 2/4/5;
  sem acesso à IaC, entregar resumo e manter **aguardando sincronização**. Conclusão
  exige aceites e retorno; pendência/transferência não é problema resolvido.
