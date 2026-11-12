# Issue: parâmetro `alarm` serializa VALARM inválido e o update apaga VALARM canônico

- **Status:** resolvida no código; regressões e verificações locais passaram em 2026-11-12
- **Prioridade sugerida:** P1 — o alarme criado pelo servidor não é reconhecido por nenhum cliente de calendário, e o caminho de update destrói alarmes de eventos criados fora do servidor
- **Identificada em:** 2026-11-04, teste funcional do servidor MCP `khan-calendar` 0.4.0 no runtime global (imagem `sha256:7363f232…`, tag `percival-khan-calendar:0.4.0-731a435`)
- **Owner / decisão:** Bill Kopp

## Problema

Duas falhas encadeadas no caminho de alarmes do servidor `khan-calendar`.

**Falha 1 — o create serializa o VALARM como propriedade textual.** Em
`src/percival_khan_calendar/adapters/khal_adapter.py:267`, o create usa
`ev.add("valarm", _make_valarm(alarm))`. `_make_valarm` (linha 616) constrói
corretamente um componente `icalendar.Alarm` — mas `Event.add` grava um
**componente** como se fosse um **valor de propriedade**. O `.ics` resultante
contém uma linha:

```
VALARM:VALARM({'ACTION': vText(b'DISPLAY'), 'TRIGGER': vDDDTypes(-1 day, 23:30:00, Parameters({}))})
```

em vez do sub-componente RFC 5545:

```
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-PT30M
END:VALARM
```

O valor gravado é o `repr` textual do dict Python do componente. Nenhum cliente
RFC 5545 — nem o `khal` — reconhece aquilo como um alarme: o evento é criado,
aparece na agenda, e o alarme **não dispara**.

**Falha 2 — o update apaga VALARM canônico vindo de fora.** O copy-through do
update (`khal_adapter.py:332`, laço `for prop in old_ev`) itera as
**propriedades** do evento antigo e não cobre **sub-componentes**. Em
`icalendar`, um VALARM corretamente formado é um sub-componente: ele não
aparece na iteração de propriedades, e `old_ev.get("VALARM")` devolve `None`.
Logo, quando `khan_update_event` reescreve um evento cujo `.ics` foi
produzido por outro cliente (ou por uma versão corrigida do próprio servidor),
o VALARM é silenciosamente descartado.

As duas falhas são acopladas e a ordem importa: corrigir apenas a falha 1
tornaria a falha 2 **mais visível**, porque passaria a existir um VALARM
canônico no disco que o update apagaria.

## Evidência e escopo

- Ambiente: workspace `f3-0-1-khan-workspace-20261020T172539Z` montado em
  `/data` com `rw`, `network: none`, `khal.conf` coerente com o layout
  (confirmado por `khan_get_status`), `icalendar` 7.2.2 na imagem.
- `khan_create_event` com `alarm="30m"` grava no disco a linha `VALARM:` com o
  `repr` do dict, conforme acima; sem `BEGIN:VALARM`, sem `TRIGGER:-PT30M`.
- Parse do arquivo gravado com `icalendar` 7.2.2: `ev.subcomponents == []` e
  `ev["VALARM"]` é um `vText`, não um `Alarm`. Ou seja, o arquivo não contém
  um alarme — contém uma propriedade de texto que só diz "VALARM".
- Reprodução isolada no venv do repositório: `ev.add_component(alarm)` emite
  `BEGIN:VALARM` / `ACTION:DISPLAY` / `TRIGGER:-PT30M` / `END:VALARM`;
  `ev.add("valarm", alarm)` emite a linha inválida. A diferença é a API
  usada, não a construção do `Alarm`.
- Simulação do copy-through do update sobre um `.ics` externo canônico
  (com `BEGIN:VALARM`/`END:VALARM`): após o update, `subcomponents == []` e o
  VALARM desapareceu. As propriedades copiadas foram `[]`, porque a
  iteração não percorre sub-componentes.
- `RRULE` funciona (`RRULE:FREQ=WEEKLY` gravado e exibido na agenda) porque
  RRULE é uma **propriedade**, não um sub-componente. A assimetria entre
  RRULE e VALARM é a mesma causa-raiz, com sintomas opostos.
- Nenhum teste de regressão cobre a serialização: `tests/` cita VALARM
  apenas em `test_security_round2.py:98`, que valida entrada inválida de
  `_make_valarm` (bugs 43/44). O caminho de serialização não é testado.
- O contrato público de tools não muda com a correção: `alarm` já é aceito
  por `khan_create_event` e o README já promete "Create events with alarms".
  A falha é de implementação, não de contrato.

### Escopo deliberadamente excluído

- O schema de `khan_update_event`, que exige `new_title` e `new_start` apesar
  de a docstring dizer que string vazia mantém o valor, é uma inconsistência
  **separada**. Mudar o schema é breaking change no contrato público e exige
  coordenação com o consumidor Nanobot (`AGENTS.md`, "MCP contract surface").
  Fica registrado aqui como observação, não como parte desta correção.
- A origem da imagem `percival-khan-calendar:0.4.0-731a435` já tem hash de
  commit no tag; o re-pin para a imagem corrigida exigirá autorização
  explícita do operador, conforme `AGENTS.md`.

## Critérios de aceite

- `khan_create_event` com `alarm` grava no `.ics` um sub-componente VALARM
  RFC 5545 válido, com `ACTION:DISPLAY` e `TRIGGER` correspondente ao
  deslocamento pedido (`15m` → `TRIGGER:-PT15M`, `1h` → `TRIGGER:-PT1H`,
  `2d` → `TRIGGER:-P2D`).
- O `.ics` resultante é parseado por `icalendar` com um `Alarm` em
  `ev.subcomponents`, e o `TRIGGER` é lido como o `timedelta` pretendido.
- `khan_update_event` sobre um evento com VALARM canônico — gravado por
  qualquer cliente, não só por este servidor — **preserva** o VALARM.
- `khan_update_event` sobre um evento gravado por este servidor também
  preserva o VALARM, e o `UID` e o `RRULE` continuam preservados como antes.
- Regressão automatizada que falha sem o patch: criação com `alarm`
  resulta em `BEGIN:VALARM` no arquivo, e update de um `.ics` com VALARM
  canônico mantém o sub-componente.
- `uv run pytest` verde com cobertura >= 80% (mínimo já enforced em
  `pyproject.toml`).
- `uv run --with ruff ruff check .` e `uv run --with ruff ruff format --check .`
  limpos.
- `uv run pytest --no-cov -m integration` verde, quando o binário `khal`
  estiver disponível.
- `CHANGELOG.md` atualizado em `## [Unreleased]`, com a entrada de correção
  e a nota de que a falha não alterava o contrato público de tools.
- Nenhuma mudança de nome de tool, de schema ou de nome de prompt.

## Decisões e limites

- **Correção mínima e localizada.** Trocar `ev.add("valarm", ...)` por
  `ev.add_component(...)` no create, e incluir os sub-componentes do evento
  antigo no copy-through do update. Nenhuma reescrita do adaptador é
  necessária.
- **Não usar subscript assignment.** O histórico do projeto já registrou que
  `ev["x"] = value` escolhe um serializer diferente em `icalendar` v6+ e
  quebra a forma canônica `Z` de `DTSTART`/`DTEND` (S6, `CHANGELOG.md`). A
  correção do create e do copy-through deve usar `add_component` /
  `add(...)`, nunca `ev[prop] = valor`.
- **Não duplicar a construção do `Alarm`.** `_make_valarm` (linha 616) já
  constrói o componente correto; o defeito está no uso, não na construção.
  `_make_valarm` deve continuar sendo o único ponto de construção do
  `Alarm`.
- **A regressão deve cobrir o arquivo em disco**, não apenas o retorno da
  tool. O defeito só é observável no `.ics` gravado; um teste que verifique
  apenas o objeto `Event` em memória passaria.
- **A geração do `TRIGGER` é relativa ao início do evento** e hoje é
  produzida por `a.add("trigger", -delta)`. A correção não deve alterar essa
  semântica — apenas o envelope de serialização.

## Referências

- `src/percival_khan_calendar/adapters/khal_adapter.py:267` — create com
  `ev.add("valarm", ...)`.
- `src/percival_khan_calendar/adapters/khal_adapter.py:332` — copy-through do
  update iterando propriedades, sem sub-componentes.
- `src/percival_khan_calendar/adapters/khal_adapter.py:616` — `_make_valarm`,
  construção correta do componente.
- `README.md:71` — "Create events with alarms"; `README.md:72` — "In-place
  update preserving UID, RRULE, VALARM".
- `CHANGELOG.md` — entrada S6 sobre `ev.add` vs subscript assignment.
- `tests/test_security_round2.py:98` — única menção a VALARM nos testes.

## Resolução e evidências (2026-11-12)

- Create agora anexa `_make_valarm(alarm)` por `Event.add_component`, gerando
  `BEGIN:VALARM` / `END:VALARM` em vez de uma propriedade textual.
- Update agora copia cada subcomponente do evento original usando
  `add_component(copy.deepcopy(component))`; propriedades como RRULE continuam
  no caminho de cópia existente.
- `tests/test_khal_adapter.py` verifica o arquivo persistido para `15m`, `1h` e
  `2d`, incluindo os TRIGGER textuais `-PT15M`, `-PT1H` e `-P2D` e o parse de
  TRIGGER como `timedelta`. Também cobre update com VALARM canônico externo e
  criado pelo adaptador, preservando UID, RRULE e DTSTART/DTEND em `Z`.
- Verificações executadas no checkout: `pytest` — 239 passed, cobertura 87.75%
  (inclui os 4 testes marcados de integração khal); `ruff check .` e
  `ruff format --check .` passaram.
- Contrato público não foi alterado. Não foi feito smoke contra calendário
  real nem qualificação/publicação de imagem.
