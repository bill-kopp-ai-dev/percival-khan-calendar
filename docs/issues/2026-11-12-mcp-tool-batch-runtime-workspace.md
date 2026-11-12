# Issue: duração de evento e resolução de caminho de exportação

- **Status:** corrigido e verificado localmente; runtime não requalificado
- **Identificada em:** 2026-11-12, smoke funcional das tools MCP `percival-khan-calendar`
- **Owner / decisão:** Bill Kopp
- **Severidade observada:** P2 para a limitação do runtime original; checkout local corrigido

## Observação

O smoke foi executado contra o servidor operacional. `khan_get_status` reportou
workspace `/data`, diretório de dados `/data/data`, calendário `nanobot` e
`khal.conf` coerente. A agenda de 7 dias e a listagem de 2026-11-12 não tinham
eventos.

As ferramentas de leitura testadas responderam sem erro: status, calendários,
agenda, listagem por data, busca sem correspondência, obtenção sem
correspondência e visualização mensal. `khan_delete_event_safe` em modo dry-run
recusou corretamente um identificador inexistente sem alterar o calendário.

## Observação sobre o workspace e exportação

O runtime usa o workspace persistente `/data`. Após autorização explícita de
Bill para esta batelada, as mutações foram executadas somente sobre um evento
sintético, que foi removido ao final.

Na primeira tentativa de exportação, `docs/issues/.tool-test-export.ics` e o
caminho relativo `mcp-tool-test-20261112.ics` foram recusados com
`output_path must be inside the workspace`. A forma absoluta `/data/mcp-tool-
test-20261112.ics` foi aceita e exportou um evento. O arquivo de exportação
permanece em `/data/mcp-tool-test-20261112.ics`; não há ferramenta de remoção
de arquivos do workspace nesta interface.

## Cobertura desta batelada

| Tool | Resultado |
| --- | --- |
| `khan_get_status` | Passou; workspace e configuração reportados coerentes |
| `khan_list_calendars` | Passou; calendário `nanobot` listado |
| `khan_view_agenda` | Passou; sem eventos em 7 dias |
| `khan_list_events` | Passou; sem eventos para 2026-11-12 |
| `khan_search_events` | Passou; consulta sintética sem resultados |
| `khan_get_event` | Passou; identificador sintético não encontrado |
| `khan_view_calendar` | Passou; matriz mensal retornada |
| `khan_export_ics` | Passou com caminho absoluto `/data/mcp-tool-test-20261112.ics`; caminhos relativo e de fora do workspace foram recusados |
| `khan_create_event` | Passou com evento sintético; encontrado via list/search/get/agenda |
| `khan_update_event` | Passou; horário e título alterados, UID preservado |
| `khan_delete_event` | Passou no caso sem correspondência; exclusão efetiva exercitada via confirmação de `khan_delete_event_safe` |
| `khan_delete_event_safe` | Dry-run e confirmação passaram; evento de teste removido |

## Problemas funcionais observados

O schema/documentação da tool `khan_create_event` diz que `end` aceita uma
duração (por exemplo, `30m`). A chamada com `end="30m"` foi recusada como
expressão inválida; a criação funcionou ao fornecer data/hora final explícita.
Isso indicava divergência entre a descrição pública e a validação efetiva. O
código local agora interpreta durações positivas como tempo decorrido, após
normalizar o início para UTC.

O relativo era resolvido contra o diretório de execução, apesar da documentação
prometer um caminho relativo dentro do workspace. O caminho relativo agora é
ancorado em `WORKSPACE_DIR`; traversal, destinos externos e symlinks continuam
recusados.

## Próxima ação

Implementação local registrada em
[`../plans/2026-11-12-duration-export-remediation-plan.md`](../plans/2026-11-12-duration-export-remediation-plan.md).
As correções foram verificadas por regressões locais. A identidade do runtime
que respondeu ao smoke original não foi determinada, portanto a correção em
runtime continua sem verificação.

## Evidências do teste autorizado (2026-11-12)

- Bill autorizou explicitamente o teste no workspace persistente `/data`; a
  autorização está registrada no README.
- Evento sintético criado para 2026-11-13, atualizado de 10:00–10:30 para
  10:15–10:45 e removido com confirmação. O UID permaneceu estável durante o
  update. Busca e listagem finais confirmaram ausência do evento.
- Exportação aceitou `/data/mcp-tool-test-20261112.ics` e informou ter exportado
  1 evento enquanto o fixture estava presente.

## Evidência de remediação local (2026-11-12)

- `uv` não está disponível no PATH deste ambiente; executados os testes pelo
  interpretador já instalado em `.venv/bin/pytest`.
- `./.venv/bin/pytest --no-cov tests/test_khal_adapter.py tests/test_tools_create.py tests/test_tools_status.py tests/test_security_round2.py`:
  **64 passed**. As novas regressões inspecionaram datas no `.ics`, trabalharam
  com CWD fora do workspace e confirmaram que traversal não alterou sentinela
  externa.
- `./.venv/bin/pytest`: **255 passed**, cobertura **87.90%** (limite do projeto:
  80%).
- `./.venv/bin/ruff check .`, `./.venv/bin/ruff format --check .` e
  `git diff --check`: passaram. `uv` não está disponível no PATH; foi usado o
  ambiente `.venv` existente.
- Não foi executada a regressão contra a versão anterior ao patch; runtime MCP
  não requalificado.
