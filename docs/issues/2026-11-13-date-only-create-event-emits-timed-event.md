# Issue: criação com data sem horário gera evento de uma hora

- **Status:** correção local e smoke de imagem cache-bust implementados; sem recibo de scan/SBOM nem qualificação Positronic
- **Identificada em:** 2026-11-13, execução do plano de reconciliação Khan/Positronic
- **Owner / decisão:** Bill Kopp
- **Plano relacionado:** [`2026-11-13-positronic-khan-config-cas-remediation-plan.md`](../plans/2026-11-13-positronic-khan-config-cas-remediation-plan.md)

## Problema

O contrato de `khan_create_event` documenta `DD/MM/YYYY` como evento all-day,
mas `KhalAdapter.write_event` converte todo `start` em `datetime` UTC e, sem
`end`, define `DTEND = DTSTART + 1h`. A criação não produz `VALUE=DATE`, e a
ferramenta pode exibir o evento no horário errado em calendários locais.

## Impacto

Datas de aniversário solicitadas como dia inteiro não podem ser criadas com
segurança usando o pin atual. Usar horário à meia-noite não é equivalente a um
evento all-day e pode deslocar a exibição entre fusos.

## Escopo da correção

- `start` date-only (`DD/MM/YYYY` ou `YYYY-MM-DD`) sem `end` produz
  `DTSTART;VALUE=DATE` e `DTEND;VALUE=DATE` no dia seguinte.
- Entradas com hora, `today`, `tomorrow`, `now`, e caminhos com `dtstart`/
  `dtend` explícitos preservam o comportamento existente.
- Adicionar regressão que inspeciona o `.ics` persistido; manter formato UTC `Z`
  para eventos datetime.
- Corrigir o texto do prompt para distinguir evento date-only do default de uma
  hora para eventos com horário.

## Critério de aceite

Testes direcionados passam; a regressão confirma `VALUE=DATE` e fim exclusivo no
dia seguinte; lint/format relevantes passam; a imagem final é qualificada e
smoke confirma tools/status antes de atualizar o pin pelo gestor.

## Estado

A implementação fonte contradiz o prompt. Nenhuma data de aniversário foi
gravada no calendário persistente. O caminho canônico do calendário de teste
Positronic ainda não existe no host e precisa ser provisionado antes da
configuração RW. A correção local emite `VALUE=DATE` com `DTEND` exclusivo no
dia seguinte para os dois formatos date-only testados. Suíte completa: 257
passed, cobertura 88.07%; Ruff check/format passaram. O job gerenciado
`9cd09e13e7742b328f27e1fbac16fd0ae522e5dbe4b33b0bc6d624d424169329` falhou na
fase build (`exitCode=1`, diagnóstico `unclassified`); ainda não existe imagem
qualificada para atualizar o pin. Após `--no-cache`, a imagem local
`sha256:3a0144822140b81cf501e95706c6e4d7ad3b9009615558ce38e23d83b254e641`
passou MCP initialize/tools/status e create/list em workspace sintético; o ICS
persistido no fixture confirmou os dois valores `VALUE=DATE`. Essa imagem não
tem recibo managed nem scan/SBOM e não foi autorizada ou pinada. Não confundir
com a imagem cacheada `sha256:497f852f87a346a8c1f6b6a5cfa08db909628d7c978855a291ad30eac622173b`,
que ainda continha a implementação antiga.
