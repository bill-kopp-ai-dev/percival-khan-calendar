# Plano de correção — serialização e preservação de VALARM

**Data:** 2026-11-12  
**Issue:** [`2026-11-04-alarm-parameter-serializes-invalid-valarm.md`](../issues/2026-11-04-alarm-parameter-serializes-invalid-valarm.md)  
**Estado:** planejado; implementação e verificações ainda não executadas.  
**Owner e decisor:** Bill Kopp.

## Resultado pretendido

Corrigir as duas falhas acopladas de alarmes sem alterar o contrato MCP: eventos
criados com `alarm` devem gravar um subcomponente VALARM RFC 5545 válido, e
`khan_update_event` deve preservar alarmes canônicos já presentes no arquivo
`.ics`. Preservar também UID, RRULE, semântica do TRIGGER relativo ao início do
evento e a forma UTC `Z` de DTSTART/DTEND.

## Escopo

- Ajustar a serialização de VALARM no create em
  `src/percival_khan_calendar/adapters/khal_adapter.py`.
- Ajustar o copy-through de subcomponentes VALARM no update.
- Adicionar regressões em `tests/` verificando os bytes persistidos e o
  round-trip por `icalendar`.
- Atualizar `CHANGELOG.md` em `## [Unreleased]` e fechar a issue somente após
  cumprir os critérios de aceite.

Fora do escopo: alterar nomes ou schemas de tools/prompts, mudar a semântica de
alarmes, corrigir a inconsistência de schema documentada separadamente na
issue, publicar uma imagem ou modificar calendário real.

## Execução

1. **Create: gravar VALARM como componente.** Manter `_make_valarm` como único
   construtor e substituir a inserção como propriedade pela API de
   subcomponentes (`Event.add_component`). Não usar subscript assignment.
2. **Update: preservar subcomponentes existentes.** Ao reconstruir o novo
   `Event`, copiar os subcomponentes do evento antigo com `add_component`,
   preservando seus componentes e propriedades sem conversão para texto. Usar
   cópia independente quando necessário para não reparentear/mutar o objeto
   carregado do calendário original. Manter o copy-through existente de
   propriedades como RRULE e X-*.
3. **Regressões em disco.** Em testes do adaptador com workspace isolado:
   - criar eventos com `15m`, `1h` e `2d`; ler o `.ics` gravado, verificar
     `BEGIN:VALARM`/`END:VALARM`, parsear com `Calendar.from_ical`, confirmar
     `Alarm` em `event.subcomponents`, `ACTION:DISPLAY` e TRIGGER como
     `timedelta` de `-15 min`, `-1 h` e `-2 d`;
   - preparar um `.ics` canônico com VALARM (incluindo origem externa), executar
     update e confirmar que o alarme permanece no arquivo parseado;
   - cobrir o mesmo update para um evento criado com `alarm` pelo adaptador;
   - confirmar que UID e RRULE continuam preservados e que DTSTART/DTEND
     continuam na representação canônica `Z`.
4. **Documentação.** Registrar a correção em `CHANGELOG.md` como correção sem
   mudança de contrato público; atualizar o status e evidências da issue, sem
   declarar critérios não verificados como concluídos.

## Aceite e verificações

- Os testes regressivos verificam o arquivo `.ics` gravado, não apenas objetos
  em memória ou o texto de retorno da tool.
- O create produz `Alarm` parseável e TRIGGER correspondente aos deslocamentos
  aceitos.
- O update preserva VALARM canônico de entrada e VALARM criado pelo servidor,
  além de UID/RRULE.
- `uv run pytest` passa com cobertura mínima de 80%.
- `uv run --with ruff ruff check .` e
  `uv run --with ruff ruff format --check .` passam.
- Executar `uv run pytest --no-cov -m integration` somente se a alteração
  afetar ou deixar dúvida no limite com khal; os testes de serialização direta
  devem cobrir o comportamento principal.
- Contrato MCP permanece inalterado: mesmas 12 tools, 6 prompts e 1 resource;
  nenhum schema ou nome é alterado.

## Riscos e controles

- **Regressão no serializer de datas:** manter o padrão `.add(...)` e verificar
  DTSTART/DTEND em `Z`; não usar `event[key] = value`.
- **Subcomponentes mutáveis/reparenting:** copiar VALARM antes de anexá-lo ao
  novo evento se a API da biblioteca associar o componente ao pai.
- **Teste falso positivo em memória:** reler e parsear o arquivo persistido em
  todos os casos de serialização.
- **Compatibilidade:** fix local, sem mudança de contrato; executar a suíte
  canônica e lint/format conforme convenções do projeto.

## Estado e próximo passo

Nenhuma implementação, teste ou atualização de changelog foi feita por este
plano. Próximo passo: executar os passos 1–4, rodar as verificações de aceite e
então atualizar issue e plano com resultados observados.
