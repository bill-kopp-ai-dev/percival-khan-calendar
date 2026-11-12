# Plano de correção — duração de eventos e caminhos de exportação

- **Data:** 2026-11-12
- **Estado:** implementação local e verificações concluídas; runtime não requalificado.
- **Owner e decisor:** Bill Kopp.
- **Issue de origem:** [batelada MCP de 2026-11-12](../issues/2026-11-12-mcp-tool-batch-runtime-workspace.md).
- **Checkout inspecionado:** `2a8cfe51e54fff0da43df84b8023a4c8a038bbb7`, com
alterações locais anteriores no README e na issue.

## 1. Resultado pretendido

Cumprir as duas capacidades já anunciadas nas descrições públicas:

1. `khan_create_event(end="30m")` deve criar um evento cujo término seja 30
   minutos após o início informado.
2. `khan_export_ics(output_path="backup.ics")` deve exportar para
   `<WORKSPACE_DIR>/backup.ics`, independentemente do diretório de execução.

Manter nomes, argumentos, tipos e defaults das 12 tools, 6 prompts e 1 resource.
As correções realizam o comportamento documentado, sem exigir novo schema MCP.
Preservar a serialização UTC `Z`, as proteções de caminhos, o lock e a escrita
atômica existentes.

## 2. Evidência e diagnóstico

| Item | Observação no servidor | Evidência no checkout | Classificação |
| --- | --- | --- | --- |
| Duração em `end` | `end="30m"` foi recusado; data/hora final explícita funcionou | `tools/create_event.py:42` promete duração; `adapters/khal_adapter.py:254-259` envia todo `end` não vazio a `_parse_khal_time`, que não interpreta durações | Divergência funcional confirmada no smoke; mecanismo compatível com o código inspecionado |
| Exportação relativa | `mcp-tool-test-20261112.ics` foi recusado; `/data/mcp-tool-test-20261112.ics` exportou 1 evento | `tools/status.py:78` promete caminho relativo; linhas 90-103 usam `Path(output_path).resolve()` sem ancorar no workspace | Dependência indevida do diretório de execução; deve ser reproduzida localmente com CWD externo |
| Caminho externo | Destino não aceito pelo confinamento foi recusado | `output.relative_to(workspace)` impõe o limite | Proteção esperada, não um defeito a remover |

O digest/commit da imagem que respondeu às tools não foi identificado nesta
batelada; não equiparar automaticamente o runtime ao checkout local. Os
diagnósticos acima vêm da comparação entre respostas observadas e código lido.

### Limites da evidência anterior

- A exportação informou sucesso; o arquivo exportado não foi aberto e parseado
  pelo cliente MCP. As regressões propostas abaixo cobrirão seu conteúdo.
- `khan_delete_event` foi chamado apenas sem correspondência. A exclusão real
  foi exercitada em `khan_delete_event_safe(confirm=True)`; isso não comprova o
  caminho de sucesso da outra tool.
- Alarmes, recorrências e todos os formatos possíveis não foram cobertos pelo
  smoke. Não descrever a batelada como validação exaustiva das 12 tools.

## 3. Escopo e decisões técnicas propostas

### A. Interpretar duração somente no término do create

Recomendação: implementar o suporte anunciado, em vez de retirar a promessa da
documentação. Manter a lógica em um helper específico do adaptador, separado do
parser geral de datas, para que durações não passem a ser aceitas como `start`
nem alterem implicitamente `new_end` no update.

- Gramática proposta: inteiro ASCII estritamente positivo seguido de unidade
  minúscula `s`, `m`, `h` ou `d`; exemplos `30m`, `2h`, `1d` e `45s`.
- Uma unidade por expressão; rejeitar `0m`, valores negativos, decimais,
  expressões compostas e unidades desconhecidas. A documentação deve explicitar
  essa gramática, sem sugerir um parser irrestrito de linguagem natural.
- Duração significa tempo decorrido: `fim_UTC = início_UTC + timedelta(...)`.
  `1d` equivale a 24 horas, inclusive ao atravessar uma mudança de horário de
  verão. Não significa o mesmo horário civil no dia seguinte.
- Preservar a precedência atual: `dtend` explícito do adaptador > `end`
  informado > duração padrão de uma hora. Durações partem do início efetivo,
  inclusive quando `dtstart` é fornecido diretamente.
- Continuar aceitando as datas/horas finais já suportadas. Não acrescentar uma
  validação geral de ordem cronológica para datas explícitas nesta correção.
- Converter entrada inválida, magnitude não representável e overflow da soma
  em `KhanValidationError`, sem criar arquivo parcial nem expor traceback.
- Manter `Event.add(...)` e normalização por `_to_utc_z`; não reutilizar a
  montagem de VALARM como parser nem mudar a semântica de alarmes.

### B. Ancorar exportação relativa no workspace

Recomendação: aceitar caminhos relativos ao workspace, como já prometido, em
vez de tornar obrigatórios caminhos absolutos.

1. Resolver `WORKSPACE_DIR` para obter a base canônica.
2. Para entrada vazia, selecionar `<workspace>/export.ics`.
3. Para entrada relativa, construir `workspace / entrada`; para absoluta,
   preservar a entrada. Fazer isso antes de `lstat()` e `resolve()` do destino.
4. Manter a recusa do arquivo-destino quando ele próprio é symlink, inclusive
   quando aponta para dentro do workspace.
5. Resolver o candidato com `strict=False` e verificar que permanece dentro do
   workspace. Recusar traversal e redirecionamento por diretório symlink para
   fora, sem criar ou modificar arquivos externos.
6. Manter lock, limite de tamanho, contagem de VEVENT, escrita atômica e resposta
   com basename. Preservar o tratamento sanitizado de falhas.

Não criar diretórios pais automaticamente. Exportação em subdiretório existente
é suportada; pai ausente continua produzindo falha controlada. Não ampliar o
escopo para reescrever todo o mecanismo de segurança de filesystem.

## 4. Sequência de execução e entregáveis

### Etapa 1 — Reproduzir com regressões direcionadas

- Usar `isolated_workspace`, datas fixas e arquivos temporários das fixtures.
- Em `tests/test_tools_create.py`, chamar a tool real com `end="30m"`, sem mock
  de `write_event`, e inspecionar o `.ics` persistido.
- Em `tests/test_tools_status.py`, fixar CWD fora do workspace com
  `monkeypatch.chdir`, exportar para `backup.ics` e inspecionar o destino real.
- Confirmar falha das duas regressões no código atual. Isso discrimina falhas
  reais de dependências acidentais do ambiente.

### Etapa 2 — Corrigir duração e cobrir suas bordas

- Alterar `src/percival_khan_calendar/adapters/khal_adapter.py` no caminho de
  create e adicionar helper de resolução do término.
- Ampliar `tests/test_khal_adapter.py` com os casos da matriz abaixo.
- Verificar que entradas rejeitadas não deixam novo `.ics` no diretório de
  dados. Preservar os validadores de entrada existentes.

### Etapa 3 — Corrigir resolução de exportação

- Alterar a tool em `src/percival_khan_calendar/tools/status.py` — ela não está
  implementada em um arquivo separado `tools/export_ics.py`.
- Ampliar `tests/test_tools_status.py` e reutilizar/estender os casos de symlink
  em `tests/test_security_round2.py`, sem duplicar verificações equivalentes.
- Comparar bytes dos arquivos sentinela externos antes/depois das recusas.

### Etapa 4 — Alinhar documentação e rastreabilidade

- `tools/create_event.py`: descrever unidades, exemplos e referência ao início.
- `tools/status.py`: esclarecer que relativo significa relativo a
  `WORKSPACE_DIR`, não ao CWD.
- `tools/prompts.py` e `resources/docs.py`: alinhar as seções de criação e
  exportação, preservando nomes e argumentos dos prompts/resource.
- `README.md`: incluir exemplos `end="30m"`, `output_path="backup.ics"` e
  caminho absoluto equivalente; preservar a autorização já registrada.
- `CHANGELOG.md`, em `Unreleased`: registrar as duas correções.
- Atualizar a issue: substituir a severidade/justificativa antiga referente ao
  bloqueio de workspace por uma descrição das duas divergências; anexar este
  plano e, após execução, evidências efetivas e limitações remanescentes.

As etapas 2 e 3 são independentes após as regressões; a consolidação documental
e a suíte final usam ambas. Nenhuma delas depende de alteração de infraestrutura.

## 5. Matriz de testes e critérios de aceite

| Área | Casos essenciais | Evidência esperada |
| --- | --- | --- |
| Duração válida | `30m`, `2h`, `1d`, `45s`; início futuro fixo; passagem de meia-noite | Arquivo parseável por `Calendar.from_ical`; diferença DTEND−DTSTART exata; ambos em UTC `Z` |
| Fuso e duração | Início com offset e caso atravessando transição de DST em zona IANA de fixture | Soma de tempo decorrido em UTC, sem depender de relógio/CWD do host |
| Compatibilidade create | `end` vazio, data/hora explícita, `dtend` explícito, `dtstart` fornecido | Default de 1h e precedências preservados; duração relativa ao início efetivo |
| Duração inválida | `0m`, `-1m`, `1.5h`, `1h30m`, `30x`, inteiro muito grande e overflow de data | Erro de validação controlado e nenhum arquivo criado |
| Escopo do parser | `start="30m"` | Continua recusado; suporte novo restrito ao término do create |
| Export relativo | Basename e subdiretório existente, CWD externo | Arquivo somente no workspace; contagem correta e VEVENT com UID/conteúdo esperado |
| Export compatível | Entrada vazia e absoluta interna | Destino padrão e caminho absoluto continuam funcionando |
| Export confinado | Absoluto externo, `../` que escape, symlink de destino interno/externo e pai symlink externo | Recusa; sentinelas externos intactos; nenhum novo arquivo externo |
| Export falha controlada | Subdiretório pai inexistente | Erro sanitizado; nenhum arquivo parcial |
| Contrato | Tools/prompts/resource e schemas de entrada | Mesmos nomes, argumentos, tipos e defaults; descrições atualizadas |

Para os testes de conteúdo, reler o arquivo após a chamada: não basta conferir
mensagem de sucesso ou objeto `Event` em memória. Reutilizar as regressões já
existentes de contagem, tamanho de exportação e VALARM em vez de reescrevê-las.

## 6. Verificação de implementação e encerramento

Durante o desenvolvimento, executar os testes direcionados com `--no-cov`:

```bash
uv run pytest --no-cov tests/test_khal_adapter.py tests/test_tools_create.py tests/test_tools_status.py tests/test_security_round2.py
```

Após integrar as correções, executar uma vez para a revisão final do código:

```bash
uv run pytest
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
git diff --check
```

- A suíte canônica deve passar com cobertura >=80%. Registrar revisão, comando,
  contagem, cobertura e skips reais, sem transportar números de execuções antigas.
- Acrescentar/ajustar uma integração com khal em workspace isolado se houver
  dúvida sobre a leitura do evento com duração; caso a suíte canônica já execute
  essa integração, reutilizar seu resultado, sem rodá-la de novo isoladamente.
- Conferir as descrições MCP geradas e os testes de contrato existentes; não
  alterar schemas para acomodar as duas correções.
- A issue só deve ser marcada resolvida no código após os critérios acima.
  Qualificação no runtime permanece uma evidência distinta da correção local.

**Handoff:** código e documentação corrigidos, regressões passando e issue com
resultados rastreáveis. Um eventual smoke de imagem deve usar workspace
sintético e registrar a identidade exata do candidato. A autorização registrada
no README pertence à batelada anterior e não constitui autorização permanente
para novas mutações em `/data`.

## 7. Riscos, limites e recuperação

- **Semântica de duração ambígua:** documentar tempo decorrido, gramática e
  exemplos; não misturar semanas/meses ou expressões compostas nesta entrega.
- **Regressão de confinamento:** ancorar primeiro, verificar symlink e contenção
  depois; testar recusas com sentinelas em disco.
- **Diferença checkout/runtime:** não declarar o servidor ativo corrigido só
  porque os testes locais passaram. Build, troca de imagem e publicação não
  fazem parte da criação deste plano.
- **Trabalho local existente:** preservar as mudanças no README e na issue;
  revisar o diff antes de qualquer commit solicitado posteriormente.
- **Artefato anterior:** o smoke deixou `/data/mcp-tool-test-20261112.ics`.
  Registrar sua existência; não confundir esse backup com evento ativo nem
  removê-lo como efeito colateral da correção.
- **Recuperação:** corrigir ou reverter apenas as alterações desta implementação
  se as regressões falharem; nunca restaurar todo o workspace ou apagar dados
  reais para satisfazer testes.

## 8. Checklist de execução

- [ ] Confirmar por execução que as duas regressões falham no código anterior (não executado); as novas regressões passam com a correção.
- [x] Durações implementadas e arquivo persistido verificado.
- [x] Exportações relativas ancoradas no workspace e confinamento preservado.
- [x] Descrições, exemplos, changelog e issue alinhados.
- [x] Suíte canônica, lint/format e verificação de diff registrados.
- [x] Evidência local distinguida de eventual qualificação do runtime.

Estado atualizado após a implementação local. A regressão contra o código
anterior não foi executada; a suíte canônica e as verificações estáticas
passaram: `./.venv/bin/pytest` **255 passed**, cobertura **87.90%**;
`ruff check`, `ruff format --check` e `git diff --check` limpos. Esta evidência
não qualifica o runtime que respondeu ao smoke.
