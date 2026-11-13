# Plano: reconciliar configuração CAS e qualificar Khan Calendar no Positronic

- **Estado:** em execução; candidato local sem-cache passou smoke all-day; bloqueado por buildArgs/associação global não editáveis e pelo validator do manager não enxergar o mount host
- **Issue:** [`2026-11-13-positronic-khan-config-cas-after-image-pin.md`](../issues/2026-11-13-positronic-khan-config-cas-after-image-pin.md)
- **Owner e decisor:** Bill Kopp
- **Servidor:** Positronic `khan-calendar` (escopo global)
- **Imagem atualmente pinada:** `sha256:d695db5075b774c0b2d8ee904f166d8400239ad6d6419fe15928fc986c072393`

## Resultado esperado

Restabelecer uma configuração válida e reconhecida pelo gestor Positronic,
preservando CAS e isolamento do calendário de teste; validar o servidor pelo
mesmo caminho gerenciado usado pelo agente; e registrar, sem duplicação, as
ocorrências de aniversário solicitadas para 2027–2030 no calendário de teste
persistentemente montado.

O pedido corresponde a 12 ocorrências únicas: três nomes × quatro anos. Não
usar `recurrence="yearly"`, pois essa opção cria uma regra sem limite final; o
intervalo solicitado termina em 2030. Usar eventos de data inteira somente se o
contrato da tool produzir `DTSTART`/`DTEND` como datas RFC 5545, não como eventos
de horário à meia-noite.

## Estado conhecido e limites

- `positronic mcp server show/list`: `khan-calendar` ativado, revisão do
  servidor `14`, `configurationId` `2c95a860-73c0-4ddf-aed5-8ab153b3defa`, pin
  no ID acima.
- `positronic mcp server discover khan-calendar` responde
  `configure the server before discovering tools`.
- `positronic mcp server inspect` não fornece revisão CAS da configuração.
- O arquivo local `~/.positronic/mcp/servers/khan-calendar.json` tem revisão
  `1` e `configurationId` `75905b35-9c79-43ee-b65b-c1e6d8022a13`, divergentes
  do registro do servidor. Tratar esse arquivo como evidência legada, não como
  fonte para uma mutação.
- Tentativas anteriores com `configure` usando `14` e `1` terminaram em
  conflito CAS. Não repetir esses valores sem nova evidência suportada.
- O pin atual passou smoke direto da imagem em workspace tmpfs (`initialize`,
  12 tools, `khan_get_status`, `khan_list_calendars`, encerramento stdio). Esse
  resultado não qualifica o gestor.
- O runbook registra caminhos de calendário de teste Positronic; o mount
  persistente exato e seu conteúdo ainda devem ser confirmados antes de
  qualquer escrita.

## Execução em 2026-11-13

- `positronic mcp server show/list` confirmaram novamente revisão `14`, mesmo
  `configurationId`, pin esperado e servidor ativo; `discover` continua
  respondendo `configure the server before discovering tools`.
- A revisão passada a `configure <id> <revision>` é a revisão da configuração,
  não a revisão do servidor. O código do manager instalado (`0.1.0-dev`, build
  `f09a5cdfbbfc.dirty.d027147f21d6`) compara esse argumento à revisão do perfil
  reconhecido; quando o `configurationId` salvo difere do servidor, o loader
  não reconhece o perfil e o CAS inicial esperado é `0`. Isso explica os
  conflitos ao usar `14` e `1`; não foi feita nova tentativa.
- Na primeira inspeção, o caminho canônico ainda não existia. Depois do comando
  privilegiado de Bill, um mount read-only via Docker confirmou no host
  `1000:1000`, modo `0770`, diretório sem symlink.
- A correção local faz `DD/MM/YYYY` e `YYYY-MM-DD` sem `end` emitirem
  `DTSTART;VALUE=DATE` e `DTEND;VALUE=DATE` no dia seguinte. Suíte completa:
  257 passed, cobertura 88.07%; Ruff check e format passaram.
- O build gerenciado foi submetido uma vez (`requestId` CLI
  `4caa314b-a2c0-4f11-971e-f43f78a08965`, job
  `9cd09e13e7742b328f27e1fbac16fd0ae522e5dbe4b33b0bc6d624d424169329`) para
  commit `486ae19b642904d3d1fa84340296e7d55d0e8fa2`, worktree dirty e contexto
  `19a8b975e333c42dad82dafde93ef1f33cb41740951c07e9c4b0a754dd473ea7`. O
  executor chegou à fase `build` e falhou com exit code `1`, stderr de 6357
  bytes e diagnóstico `unclassified`; não há image ID verificado nem recibo
  scan/SBOM elegível. O estado foi consultado pelo mesmo job; não houve replay.
- Após o build local de diagnóstico abaixo, uma segunda submissão intencional
  com a fonte/documentação final (`requestId` CLI
  `8519ef31-0688-4995-9dd1-5889825ea7bb`, job
  `8c1de0ca0bbe4af9200188801f2c887e941f86c4831a425b3173e7f458105aa9`) também
  falhou na fase `build`, exit code `1`, diagnóstico `unclassified`, stderr
  6012 bytes; contexto
  `adb70f90ced87d7291d58533731eb47937673ad71fb1021e8d01577f60425d4a`. O
  segundo job terminou e foi consultado; nenhum job está pendente.
- Build de diagnóstico em cache-only passou com Docker Buildx local usando
  plataforma `linux/amd64`, rede `default`, `VERSION=0.4.0` e
  `GIT_SHA=486ae19-dirty`. Isso valida os passos do Dockerfile, mas não produziu
  imagem carregada, scan/SBOM nem recibo gerenciado; não autoriza o pin.
- Uma segunda tentativa local com `--no-cache --load` passou, inclusive
  consultando o Snapshot Debian (sem 503/504), e carregou
  `sha256:3a0144822140b81cf501e95706c6e4d7ad3b9009615558ce38e23d83b254e641`
  como `khan-calendar:all-day-0.4.0-486ae19-dirty-nocache`. No MCP stdio
  direto, versão do servidor, 12 tools, status isolado `/data`, criação e
  leitura via `khan_list_events` passaram; o `.ics` sintético contém
  `DTSTART;VALUE=DATE:20270306` e `DTEND;VALUE=DATE:20270307`, e a listagem
  mostra a ocorrência sem horário. O conteúdo foi descartado com o workspace
  temporário.
- Uma imagem local anterior, `sha256:497f852f87a346a8c1f6b6a5cfa08db909628d7c978855a291ad30eac622173b`,
  foi construída com cache e continha o código anterior (datetime + uma hora);
  smoke a identificou e ela **não deve ser usada**. Nenhuma das duas imagens
  recebeu scan/SBOM ou autorização do gestor.
- O effective recipe atual reporta `association: not-configured`,
  `scanGate: report-only`, rede `default`, plataforma `linux/amd64` e não expõe
  `buildArgs`/`versionFile`. Os dois jobs gerenciados expõem somente stderr
  ocultado (`unclassified`, bytes), inclusive com `--print-logs`; a causa
  exata do erro host permanece não demonstrada. O build local sem-cache mostra
  que a fonte atual e o snapshot Debian funcionam por Docker local, mas não
  prova qual comando/args o executor usou.
- Docker CLI, Engine e Buildx locais respondem (`29.9.2`, Engine `29.9.2`,
  Buildx `v0.39.0`), mas isso não transforma o job gerenciado falho em recibo
  válido.
- Embora o Docker host agora veja o diretório canônico como `1000:1000 0770`,
  `positronic mcp server configure khan-calendar 0 ...` falhou com
  `mount source does not exist` no processo do manager/CLI da sessão. O path
  existe no host Docker mas não está visível no namespace do agente, portanto
  o validator local do manager não consegue aceitá-lo. Não tentei substituir o
  destino nem criar um placeholder no namespace isolado.
- Build local direto sem args reproduziu falha no primeiro `RUN` do Dockerfile:
  `VERSION '' must match pyproject.toml ('0.4.0')`; com `VERSION=0.4.0` e
  `GIT_SHA=486ae19-dirty`, o build local sem-cache passa. Isso torna ausência ou
  valor incorreto de build args uma hipótese forte para os jobs managed, mas
  não prova a causa exata: stderr/args do executor não são expostos e a policy
  efetiva omite `buildArgs`/`versionFile`.
- O `managedServerId` em project capsule só é verificado pelo executor para um
  servidor local atribuído ao projeto; o servidor atual é global. O recipe
  permanece `association: not-configured`, e a interface de runtime policy não
  oferece campo editável para a associação global.
- Nenhuma configuração, pin, mount ou ocorrência persistente foi alterada.
  Permanecem bloqueadas a qualificação gerenciada/autorização do candidato,
  reconfiguração do gestor e criação/verificação das 12 ocorrências.

### Retomada após provisionamento do operador

- Bill executou `sudo install -d -o 1000 -g 1000 -m 0770` no caminho canônico.
  Um bind mount read-only via Docker host confirmou diretório real, `1000:1000`,
  modo `0770`, sem symlink no componente `positronic-test-mcp/khan-calendar`.
- Repeti a tentativa suportada de configuração com CAS `0`, rede `none`, mount
  canônico RW, `KHAN_WORKSPACE_DIR=/data` e allowlist somente de leitura. O
  manager/CLI retornou `mount source does not exist`; o caminho existe no Docker
  host, mas não está visível no namespace que valida a configuração. Não gravei
  configuração nem usei path alternativo/placeholder.
- Um build Docker local sem `VERSION` falha no primeiro passo com
  `VERSION '' must match pyproject.toml ('0.4.0')`; com `VERSION=0.4.0` e
  `GIT_SHA=486ae19-dirty` passa. Como os dois jobs host só expõem
  `unclassified` e não publicam `buildArgs`/`versionFile`, falta prova para
  confirmar se essa é a causa exata, embora seja uma hipótese consistente.
- `positronic mcp maintenance capabilities` continua mostrando
  `association: not-configured`; `managedServerId` de cápsula só associa, na
  implementação observada, servidor local atribuído ao projeto. O Khan continua
  global e a API de runtime policy não oferece campo editável para o vínculo
  global. Sem isso, não há autorização managed elegível para o build local.
- Estado final desta retomada: pin `d695db...`, revisão de servidor `14` e
  `configurationId` `2c95a860-73c0-4ddf-aed5-8ab153b3defa` permanecem; CAS `0`
  não foi aplicado; nenhum evento persistente foi criado.

## Escopo

### Incluído

1. Obter o estado de configuração autoritativo e uma revisão CAS atual por uma
   interface suportada do gestor.
2. Restaurar ou reaplicar a configuração mínima para o servidor global,
   mantendo rede `none`, allowlist limitada e mount gravável exclusivamente
   para o calendário de teste Positronic.
3. Qualificar handshake, descoberta, leitura segura, chamada de escrita e
   encerramento através do gestor.
4. Confirmar e, se necessário, corrigir a semântica de eventos de data inteira
   antes de criar as 12 ocorrências delimitadas a 2027–2030.
5. Verificar cada ocorrência e estado final sem divulgar conteúdo de outros
   eventos do calendário.

### Fora de escopo

- Usar ou montar o calendário real do operador, dados Percival ou qualquer
  workspace não identificado como teste Positronic.
- Editar manualmente registry, arquivo de configuração, audit ou estado
  interno do Positronic; contornar o gestor com `docker run` para escrita
  persistente; adivinhar/repetir CAS conflitante.
- Criar eventos com recorrência aberta, alarmes, horários, descrição ou local
  não solicitados.
- Remover dados preexistentes ou apagar os eventos solicitados após a
  validação. As ocorrências pedidas permanecem como dados do calendário de
  teste.

## Hipóteses e evidência discriminante

| Hipótese | Evidência que apoia | Evidência que enfraquece/falsifica | Decisão operacional |
| --- | --- | --- | --- |
| A configuração de MCP foi invalidada na troca do image pin e não foi reaplicada | `discover` pede configuração; `configurationId` do registro diverge do arquivo local | Interface suportada apresenta configuração válida e `discover` funciona sem alteração | Reconfigurar apenas depois de obter CAS atual; caso contrário, usar o fluxo suportado de recuperação |
| O arquivo local é um snapshot antigo, não a revisão autoritativa atual | Revisão local `1`, UUID diferente do UUID no registro, e chamadas antigas conflitaram | Gestor confirma explicitamente esse arquivo e fornece mecanismo CAS compatível | Não usar seus números como expected revision; não editá-lo |
| Datas sem horário já são eventos de dia inteiro | Documentação de prompts afirma `DD/MM/YYYY` → all-day | Implementação observada cria `datetime` UTC e, sem `end`, atribui duração de 1 hora | Fazer probe em workspace descartável e inspecionar resposta/ICS antes de gravar no calendário persistente |

## Plano de execução

### Fase 1 — Preservar estado e obter CAS correto

1. Registrar em uma única fotografia de leitura: `show`, `inspect`, revisão e
   `configurationId` do servidor, imagem pinada e resultado de `discover`.
2. Pela TUI ou API/CLI suportada do Positronic, identificar se existe uma
   configuração persistida, seu status (válida, invalidada ou ausente), sua
   revisão CAS esperada e o procedimento suportado de restore/reconfigure.
3. Se a interface não expuser a revisão, parar antes de mutar. Abrir/encaminhar
   a falha ao gestor Positronic para que a interface exponha CAS/estado ou
   forneça recuperação suportada. Não inferir CAS a partir de `server.revision`,
   do UUID, do arquivo legado ou de revisões de outros recursos.
4. Se houver backup suportado de configuração, comparar apenas campos
   necessários (rede, origem/destino do mount, env, allowlist); não restaurar
   um backup de conteúdo de calendário nem copiar arquivos de estado à mão.

**Saída da fase:** procedimento e CAS de configuração autoritativos conhecidos,
ou bloqueio documentado sem mudança de estado.

### Fase 2 — Confirmar o destino isolado e configurar pelo gestor

1. Consultar o runbook vigente e confirmar o caminho autorizado do calendário
   persistente Positronic de teste. Verificar que é o destino de Khan Positronic,
   não Percival, não calendário de produção e não o antigo diretório de fixture
   por inferência.
2. Antes do mount RW, validar que o diretório existe, pertence ao contexto de
   teste esperado e não redireciona por symlink para outro dado. Se o destino
   exato não puder ser provado, manter a escrita bloqueada.
3. Usando a interface suportada e o CAS confirmado, salvar configuração com:
   - rede `none`;
   - somente o mount autorizado `<caminho-de-teste-confirmado>|/data|rw`;
   - `KHAN_WORKSPACE_DIR=/data`;
   - allowlist mínima para `khan_get_status`, `khan_list_calendars`,
     `khan_list_events`, `khan_search_events` e `khan_create_event`;
   - nenhum secret/env adicional, nenhum mount de host amplo e nenhuma
     permissão de delete/update/export para esta batelada.
4. Não desativar ou reativar o servidor se a configuração puder ser aplicada
   com segurança sem essa transição; se a interface exigir, observar a revisão
   atual e usar a sequência CAS documentada, sem repetir aceites.
5. Confirmar pelo gestor o novo `configurationId`/revisão, depois executar
   `discover`. Se a configuração invalidar novamente ou a resposta não
   corresponder ao workspace previsto, parar e não chamar tool de escrita.

**Saída da fase:** servidor configurado, `discover` lista somente tools
autorizadas, mount e env confirmam o destino isolado.

### Fase 3 — Smoke funcional pelo caminho Positronic

1. Pelo gestor, verificar `initialize` e `tools/list`; confirmar os nomes
   necessários e registrar contagem, sem aceitar tool extra não prevista.
2. Chamar `khan_get_status`; exigir que reporte o workspace `/data`, calendário
   default esperado e configuração coerente. Parar se apontar para qualquer
   destino real ou diferente.
3. Chamar `khan_list_calendars`; confirmar que `nanobot` está configurado.
4. Chamar uma leitura segura em período próximo a cada data solicitada para
   detectar eventos já existentes com o mesmo título/data. Comparar título e
   data sem expor conteúdo de outros eventos. Para correspondências existentes,
   não criar duplicata; registrar como já presente e verificar somente o que
   for necessário.
5. Encerrar a sessão MCP normalmente e verificar que o processo termina após
   EOF, sem timeout do broker/cliente.

**Saída da fase:** prova protocolar pelo gestor e baseline de duplicatas
concluídos antes da primeira escrita.

### Fase 4 — Qualificar semântica de data inteira

1. A implementação atual de `KhalAdapter.write_event` converte `start` em
   `datetime` UTC e, quando `end` está vazio, define `DTEND = DTSTART + 1h`.
   Portanto, o comportamento de `DD/MM/YYYY` como evento all-day documentado
   ainda não foi confirmado; não presumir que seja `VALUE=DATE`.
2. Em workspace descartável separado do mount persistente, chamar
   `khan_create_event` com uma data sintética `DD/MM/YYYY`; ler o resultado pela
   tool e inspecionar o arquivo `.ics` do fixture descartável.
3. Critério do probe: `DTSTART;VALUE=DATE` e `DTEND;VALUE=DATE` no dia seguinte,
   sem horário e sem fuso. Se o probe resultar em datetime/1h, não gravar as
   ocorrências do usuário ainda.
4. Se houver divergência, abrir issue de comportamento, corrigir o contrato e
   adicionar teste de regressão em unidade/protocolo. Qualificar a suíte
   relevante (`pytest`, ruff quando houver Python) antes de construir a nova
   imagem. Como qualquer novo pin invalida a configuração, executar build/scan/
   SBOM e atualização de pin pela workflow do owner; reaplicar a configuração
   pelo CAS novo e repetir as fases 2–3 uma vez para a imagem final.
5. Se o probe confirmar dia inteiro, reutilizar a imagem já pinada sem build
   redundante.

**Saída da fase:** semântica de dia inteiro observada e correta para a imagem
que será usada nas criações, ou tarefa interrompida até correção e novo pin.

### Fase 5 — Criar as 12 ocorrências delimitadas

Criar eventos one-off, sem RRULE, somente para as combinações abaixo. A data
deve ser passada como `DD/MM/YYYY` se a fase 4 comprovar que isso gera um evento
all-day no runtime:

| Título | 2027 | 2028 | 2029 | 2030 |
| --- | --- | --- | --- | --- |
| Aniversário da Mara | 06/03/2027 | 06/03/2028 | 06/03/2029 | 06/03/2030 |
| Aniversário de Namoro | 18/06/2027 | 18/06/2028 | 18/06/2029 | 18/06/2030 |
| Aniversário de noivado | 13/07/2027 | 13/07/2028 | 13/07/2029 | 13/07/2030 |

Procedimento:

1. Revalidar status/workspace e duplicatas imediatamente antes das escritas.
2. Criar somente as combinações ausentes. Não criar recorrência indefinida nem
   preencher anos anteriores/posteriores ao intervalo acordado.
3. Após cada chamada, registrar o UID retornado e confirmar que a resposta não
   indica erro. Se houver timeout/resposta incerta, pesquisar por título/data
   antes de repetir a chamada; não duplicar um efeito incerto.
4. Ler cada data no calendário pelo gestor e confirmar os 12 títulos, datas,
   valores all-day e ausência de itens fora do intervalo. Se algum já existia,
   distingui-lo do que foi criado nesta execução e não alterar o existente.
5. Não executar delete de limpeza: os 12 eventos são a tarefa solicitada e
   devem permanecer no calendário de teste.

## Verificações e evidência a registrar

- Identidade: image ID, versão/label, revisão do servidor, `configurationId` e
  revisão CAS da configuração final.
- Rede, mount (origem e destino), modo RW, env `KHAN_WORKSPACE_DIR` e allowlist
  efetiva — sem imprimir conteúdo de variáveis secretas.
- `discover`, contagem e nomes de tools, respostas de status/listagem,
  encerramento stdio.
- Probe de data inteira: chamada, representação efetiva do evento/ICS e
  workspace descartável usado.
- Tabela das 12 combinações: estado preexistente/criado, UID (quando criado),
  resultado de leitura posterior. Redigir qualquer conteúdo de evento alheio.
- Confirmar que o diretório de teste persistente foi o único destino gravável.

## Riscos e controles

| Risco | Controle |
| --- | --- |
| Escrever em calendário real ou pertencente ao Percival | Confirmar caminho Positronic de teste no runbook e via `khan_get_status`; mount somente nesse diretório |
| Sobrescrever configuração concorrente | Ler CAS atual imediatamente antes; usar interface suportada; parar em qualquer conflito |
| Duplicar evento preexistente ou chamada com timeout | Pré-busca por título/data; reconciliar pelo read antes de retry; registrar UID |
| Datas de dia inteiro virarem eventos de uma hora | Probe descartável e inspeção de `VALUE=DATE` antes de dados persistentes |
| Recorrência ultrapassar 2030 | Criar 12 eventos independentes; não usar `yearly` sem limite |
| Novo pin invalidar configuração restaurada | Fazer qualquer correção/build antes da configuração final; após o pin, reaplicar config usando CAS atual |
| Config legada expor montagem antiga/dados | Não inferir destino pelo arquivo; confirmar caminho autorizado e não ampliar mount |

## Dependências, recursos e sequência

- **Dependência externa:** gestor Positronic deve disponibilizar CAS autoritativo
  ou fluxo de recuperação de configuração que não exija editar arquivos
  gerenciados à mão.
- **Owner:** Bill Kopp para decisões de dados e operação; execução pela
  interface suportada do Positronic.
- **Recursos:** CLI/TUI Positronic, Docker Engine local quando exigido para
  smoke/build, repositório Khan e workspace persistente de teste Positronic.
- **Sequência crítica:** CAS → destino isolado → configurar → discovery/read
  smoke → qualificar dia inteiro (eventual correção/build/pin) → reconfigurar
  após novo pin se necessário → deduplicar → criar → reler e verificar.
- **Estimativa/prazo:** não estimado; depende de resolver a interface/revisão
  CAS e, possivelmente, corrigir a semântica all-day e qualificar novo pin.

## Decisão para interromper

Parar antes de qualquer escrita persistente se o CAS não puder ser obtido pela
interface suportada; se o mount não puder ser provado como o calendário de teste
Positronic; se `khan_get_status` apontar a outro workspace; se houver conflito
CAS; ou se a tool produzir evento com horário quando se espera dia inteiro.
Reportar a evidência concreta e a próxima dependência, sem tentar números
alternativos ou caminhos Docker fora do gestor.

## Registro de execução — 2026-11-13 (concluída)

Todas as fases foram executadas pelo caminho gerenciado do Positronic, sem
edição manual de registry, configuração ou auditoria. Evidência detalhada em
`docs/issues/2026-11-13-positronic-khan-config-cas-after-image-pin.md`.

| Fase | Estado | Evidência |
| --- | --- | --- |
| 1 — CAS e destino | concluída com desvio | Recipe estática no `maintenance-policy.json` do host (backup preservado) com `serverId: khan-calendar` ⇒ `association: verified`; CAS de configuração `0` aceito pelo gestor |
| 2 — destino isolado e configuração | concluída com desvio | Mount RW `/home/bill/.positronic/mcp/data/khan-calendar → /data`, rede `none`, `KHAN_WORKSPACE_DIR=/data`, allowlist de 5 tools; `configurationId 36351e71-…`, revisão de configuração `1`, servidor na revisão `15` |
| 3 — smoke pelo gestor | concluída | `khan_get_status` reporta workspace `/data`, `khal.conf` coerente e calendário `nanobot`; `khan_list_calendars` confirma `nanobot`; pré-busca "Aniversário" sem resultados; auditoria do gestor com `allowed` → `succeeded` por chamada |
| 4 — semântica de dia inteiro | confirmada | 12 `.ics` com `DTSTART;VALUE=DATE` e `DTEND;VALUE=DATE` no dia seguinte, sem `RRULE`; label da imagem `486ae19…-dirty` |
| 5 — criação das 12 ocorrências | concluída | 12 UIDs distintos, 12 arquivos no workspace, leitura por `khan_search_events` retorna exatamente 12; nada fora de 2027–2030 |

### Tabela das 12 combinações

| Título | 2027 | 2028 | 2029 | 2030 |
| --- | --- | --- | --- | --- |
| Aniversário da Mara | 06/03/2027 — criado | 06/03/2028 — criado | 06/03/2029 — criado | 06/03/2030 — criado |
| Aniversário de Namoro | 18/06/2027 — criado | 18/06/2028 — criado | 18/06/2029 — criado | 18/06/2030 — criado |
| Aniversário de noivado | 13/07/2027 — criado | 13/07/2028 — criado | 13/07/2029 — criado | 13/07/2030 — criado |

Nenhum evento pré-existente foi alterado; nenhuma chamada de delete foi feita.

### Identidade da imagem pinada

- Job gerenciado: `de823864b6604f8226e3d1bf9f14eaf8d1aba5465e85cba264202d1cdc2f94d3`
  (`succeeded`, 73 s).
- `imageId`/`manifestDigest`:
  `sha256:44ff7218b9b8d76133651ea26c5845f78a4980d12b3ac7f02084c8006a9eb4a6`.
- `configDigest`:
  `sha256:2611866fa2053c2c024f1d72ce35d192b2930ce3804b29c9b19891e40142ee26`.
- `commit` `486ae19b642904d3d1fa84340296e7d55d0e8fa2`, `dirty: true`,
  `contextSha256 3beb584af7aff7d54d994a387b22bec03662c462d5e5cd3c10fc5cdf5562b509`.
- Scan: `scanSha256 bc10d284f19cac4492dd5cbd54798d125a222fbfb7b48521de146326d10b84a0`,
  SBOM: `sbomSha256 22a1eb26210abad6e5ec3ae817e042da10cfe4518c076070c994c0f3ba6c3953`,
  Trivy `0.76.1`, `findings: 0` no gate `HIGH/CRITICAL`.
- Servidor: `khan-calendar` revisão `15`, `configurationId
  36351e71-1609-4fb1-b00a-be5c029c65d0`, configuração revisão `1`.

### Pendências após a execução

1. Migrar o mount para `/home/bill/.local/share/positronic-test-mcp/khan-calendar`
   (diretório canônico) em janela que permita recriar o container do agente, com
   bind same-path em `compose.json`; até lá, o destino em uso é
   `/home/bill/.positronic/mcp/data/khan-calendar`.
2. Trocar `GIT_SHA` da recipe estática de `{commit}-dirty` para `{commit}` após
   commitar a correção all-day.
3. Defeito de timeout no cleanup do caminho `discover` (`docker stop` deixa o
   container em `Dead` com auto-remove pendente; o laço de espera de 15 s do
   `execution.ts` não converge) — registrar no repositório do gestor; o caminho
   funcional da sessão não é afetado.
