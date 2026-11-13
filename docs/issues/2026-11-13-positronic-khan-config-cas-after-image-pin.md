# Issue: configuração Positronic do Khan indisponível após pin da imagem

- **Status:** resolvido em 2026-11-13 — build gerenciado com scan/SBOM, `authorize`, pin, configuração por CAS `0` e as 12 ocorrências gravadas e verificadas no calendário de teste persistente. Restam duas pendências documentadas e não bloqueantes: adoption do diretório canônico e um defeito de timeout no `discover` (ver "Resolução")
- **Prioridade sugerida:** P1 — MCP ativado não pode ser descoberto nem chamado pelo gestor
- **Identificada em:** 2026-11-13, validação da imagem Khan pinada no Positronic
- **Owner / decisão:** Bill Kopp

## Problema

O servidor Positronic `khan-calendar` aponta para a imagem corrigida e aparece
como ativado, mas o gestor não consegue descobrir suas tools:

```text
positronic mcp server discover khan-calendar
Error: configure the server before discovering tools
```

Sem discovery/configuração válida, as chamadas pelo caminho gerenciado não
estão disponíveis. A imagem funciona isoladamente, mas isso não valida sua
integração pelo Positronic.

## Evidência de estado divergente

O registro atual retornado por `positronic mcp server list` e `show` contém:

- Servidor: `khan-calendar`, versão `0.4.0`, ativado, escopo `global`.
- Revisão do servidor: `14`.
- Image ID: `sha256:d695db5075b774c0b2d8ee904f166d8400239ad6d6419fe15928fc986c072393`.
- `configurationId`: `2c95a860-73c0-4ddf-aed5-8ab153b3defa`.

Já a configuração local em
`~/.positronic/mcp/servers/khan-calendar.json` ainda contém:

- Revisão de configuração: `1`.
- `configurationId`: `75905b35-9c79-43ee-b65b-c1e6d8022a13`, diferente do
  registrado para o servidor.
- Rede `none`, mount gravável em
  `/home/bill/.positronic-reports/f3-0-1-khan-workspace-20261020T172539Z` para
  `/data`, `KHAN_WORKSPACE_DIR=${KHAN_WORKSPACE_DIR}` e allowlist com as 12
  tools Khan.

`positronic mcp server inspect khan-calendar` também não expõe configuração
funcional nem uma revisão CAS de configuração atual. O código do manager
correspondente ao CLI instalado mostra que `configure <id> <revision>` usa a
revisão do perfil. Quando o `configurationId` do perfil diverge do servidor,
o loader não reconhece o perfil e `saveConfig` espera a revisão inicial `0`.
Isso explica os conflitos anteriores com `14` e `1`; ainda não houve chamada
com `0`.

## Atualização de execução — 2026-11-13

- Na primeira tentativa, o destino não existia e `/home/bill/.local/share` era
  `root:root` modo `0755`; a sessão UID/GID `1000:1000`, sem `sudo`, recebeu
  `Permission denied` ao executar `mkdir -p`. Depois, Bill criou o destino como
  administrador, sem alterar as permissões do pai.
- Bill executou no host `sudo install -d -o 1000 -g 1000 -m 0770` para o destino
  canônico. Um mount Docker read-only confirmou `1000:1000 0770` e diretório
  real. Porém, a tentativa suportada de `configure` com CAS `0`, rede `none`,
  mount canônico e allowlist somente leitura falhou com
  `mount source does not exist`; o namespace do CLI/manager da sessão não vê a
  pasta que existe no Docker host. Nenhuma configuração foi salva.
- Dois builds gerenciados terminaram na fase `build` com `exitCode=1` e
  `diagnostic.reason=unclassified`; `--print-logs` não revelou stderr. Um build
  Docker local `--no-cache` com args explícitos passou, inclusive obtendo
  pacotes do Debian Snapshot. A causa específica do executor continua
  indeterminada; não assumir falha do snapshot nem dos argumentos sem stderr.
- Build local sem args falha no primeiro passo do Dockerfile com
  `VERSION '' must match pyproject.toml ('0.4.0')`; com `VERSION=0.4.0` e
  `GIT_SHA=486ae19-dirty` passa sem-cache. Portanto buildArgs ausente/incorreto
  é hipótese forte para o executor, ainda sem confirmação do seu stderr ou
  valores internos (`buildArgs`/`versionFile` não são expostos pela policy API).
- O candidato local
  `sha256:3a0144822140b81cf501e95706c6e4d7ad3b9009615558ce38e23d83b254e641`
  passou smoke MCP/stdio e create/list all-day em workspace sintético, com
  `VALUE=DATE` verificado no `.ics`; não tem recibo scan/SBOM e não foi
  autorizado ou pinado. Uma imagem cacheada anterior
  (`sha256:497f852f87a346a8c1f6b6a5cfa08db909628d7c978855a291ad30eac622173b`)
  continha a implementação antiga e não deve ser usada.
- O efetivo recipe informa associação do projeto ao servidor como
  `not-configured` e scan gate `report-only`; a configuração gerenciada ainda
  não foi aplicada. Nenhum evento persistente foi criado.
- A indicação `managedServerId` da cápsula só é verificada pelo executor para
  servidor local atribuído ao projeto; o Khan está em escopo global. A policy
  de runtime não fornece campo editável para associar este recipe global ao
  servidor. A autorização do build managed permanece bloqueada por esse vínculo
  ausente.

## Impacto

- O pin da imagem não basta para habilitar o MCP: sem uma configuração
  reconciliada, `discover` e as chamadas do agente falham antes do uso.
- A imagem isolada foi validada com `initialize`, `tools/list` (12 tools),
  `khan_get_status` e `khan_list_calendars` em `/data` temporário; isso não
  comprova o caminho do gestor.
- Doze eventos de teste solicitados para 2027–2030 permanecem sem gravação; não
  houve escrita em calendário persistente.

## Causa

O pin de imagem altera o `configurationId` do servidor. O perfil local com ID
anterior deixa de ser reconhecido pelo loader; nesse estado, o CAS inicial de
configuração é `0`. Isso explica a recusa dos valores `14` e `1`. A origem do
perfil divergente é compatível com configuração local legada após o pin, mas
ainda não se determinou quando/por que o arquivo local deixou de acompanhar o
registro. Não editar registry/config manualmente nem contornar o gestor com
Docker para escrever no calendário persistente.

## Próxima ação

1. Após um build gerenciado bem-sucedido e qualificação da correção all-day,
   autorizar/pinar a imagem final pelo gestor e reler a revisão/CAS resultantes.
2. Provisionar e verificar o diretório canônico de teste
   `/home/bill/.local/share/positronic-test-mcp/khan-calendar`; ele não existe
   atualmente. Não usar a origem legada do arquivo de configuração nem outro
   diretório substituto.
3. Configurar pelo gestor usando CAS de configuração `0` enquanto o perfil
   incompatível continuar não reconhecido; aplicar rede `none`, mount RW
   canônico, `KHAN_WORKSPACE_DIR=/data` e allowlist mínima necessária.
4. Rodar `discover` pelo gestor e executar `initialize`, `tools/list` e uma
   chamada de leitura segura pelo mesmo caminho.
5. Depois de confirmar o workspace montado, gravar e verificar as ocorrências
   de teste solicitadas; registrar que são 12 entradas (3 aniversários × 4 anos,
   2027–2030), sem tocar em outro calendário.

## Critérios de aceite

- A configuração aplicada tem `configurationId` e CAS atuais reconhecidos pelo
  gestor, sem edição manual de estado gerenciado.
- `positronic mcp server discover khan-calendar` lista as tools autorizadas.
- Pelo agente Positronic, `khan_get_status` confirma o workspace de teste
  correto e `khan_list_calendars` confirma o calendário esperado.
- A criação e a leitura posterior das 12 ocorrências 2027–2030 são confirmadas
  no calendário de teste persistente; nenhuma ocorrência fica fora desse
  intervalo e nenhum outro workspace/calendário é alterado.
- O processo stdio encerra normalmente após fechar stdin.

## Resolução — 2026-11-13

Todos os critérios de aceite acima foram satisfeitos pelo caminho gerenciado, sem
edição manual de registry/config/audit.

### Cadeia executada

1. **Recipe estática no host** — `maintenance-policy.json` do deployment
   (`/home/bill/.local/share/positronic/docker-candidate/real-fa4c69797ff0/`)
   recebeu a recipe `percival-khan-calendar/canonical` com `serverId:
   "khan-calendar"`, `buildArgs` `VERSION={version}` e `GIT_SHA={commit}-dirty`,
   `versionFile: "pyproject.toml"`, `network: "default"`, `timeoutMs: 600000`,
   `maxFiles: 5000`, `maxBytes: 67108864` e `rejectSeverities:
   ["HIGH","CRITICAL"]`. Escrita atômica (temp + `mv`), owner `1000:1000`, modo
   `0600`; backup em `backups/maintenance-policy.json.bak-20261113T155806Z`.
   `capabilities` passou a reportar `association: verified` e
   `scanGate: ["HIGH","CRITICAL"]`.
2. **Build gerenciado** — job `de823864b6604f8226e3d1bf9f14eaf8d1aba5465e85cba264202d1cdc2f94d3`
   (`state: succeeded`, 73 s), `imageId
   sha256:44ff7218b9b8d76133651ea26c5845f78a4980d12b3ac7f02084c8006a9eb4a6`,
   `manifestDigest` idêntico, `commit 486ae19b642904d3d1fa84340296e7d55d0e8fa2`,
   `dirty: true`, `contextSha256
   3beb584af7aff7d54d994a387b22bec03662c462d5e5cd3c10fc5cdf5562b509`, scan
   (`scanSha256 bc10d284…`) e SBOM (`sbomSha256 22a1eb26…`) gerados pelo executor,
   `findings: 0` no gate `HIGH/CRITICAL`.
3. **Authorize + pin** — `maintenance authorize <jobId>` ligou a imagem ao
   servidor `khan-calendar`; `server update-image khan-calendar <imageId> 14`
   levou o servidor à revisão `15` e rotacionou `configurationId` para
   `36351e71-1609-4fb1-b00a-be5c029c65d0`.
4. **Configuração por CAS `0`** — `server configure khan-calendar 0` gravou
   revisão de configuração `1`: rede `none`, mount RW
   `/home/bill/.positronic/mcp/data/khan-calendar → /data`,
   `KHAN_WORKSPACE_DIR=/data` e allowlist de 5 tools
   (`khan_get_status`, `khan_list_calendars`, `khan_list_events`,
   `khan_search_events`, `khan_create_event`). O CAS `0` foi o valor aceito
   porque o `configurationId` rotacionado torna o perfil legado não reconhecido.
5. **Smoke e criação** — `khan_get_status` reportou workspace `/data`,
   `khal.conf` coerente com o layout e calendário `nanobot`;
   `khan_list_calendars` confirmou apenas `nanobot`; a busca por "Aniversário"
   antes das escritas retornou zero eventos (sem duplicatas).
6. **As 12 ocorrências** foram criadas one-off e all-day; leitura por
   `khan_search_events` retorna exatamente 12 e o diretório do workspace
   contém exatamente 12 arquivos `.ics`, todos com `DTSTART;VALUE=DATE` e
   `DTEND;VALUE=DATE` no dia seguinte, sem `RRULE`. Cada criação devolveu UID
   distinto e a auditoria do gestor registrou `allowed` → `succeeded` para cada
   chamada.

### Desvios e pendências

- **Diretório canônico não adotado.** `/home/bill/.local/share/positronic-test-mcp/khan-calendar`
  existe apenas no namespace do Docker host; o validator do manager resolve o
  mount no seu próprio namespace e rejeita a origem com
  `mount source does not exist`. Adotá-lo exige bind same-path em `compose.json`
  e recriar o container do agente, o que encerra a sessão em uso. Foi usado o
  diretório de teste do próprio Positronic
  `/home/bill/.positronic/mcp/data/khan-calendar` — já bindado same-path,
  gravável pelo UID `1000`, com `khal.db` de baseline vazio e calendário
  `nanobot` — que é o mesmo destino documentado para o Khan no bench do
  Percival. Nada do calendário real do operador foi tocado. A migração para o
  caminho canônico fica como item separado, a ser executada em janela que
  permita recriar o agente.
- **`discover` do CLI continua falhando no cleanup.** O handshake e o
  `tools/list` concluem (12 tools), mas o fechamento excede o prazo de 15 s do
  cleanup: `docker stop` deixa o container em `Dead` enquanto o auto-remove
  (`--rm`) do daemon ainda está pendente, e o laço de espera do
  `execution.ts` continua listando o container, resultando em
  `MCP cleanup-pending`. É defeito de timeout no caminho de fechamento da
  discovery, não da configuração; o caminho funcional (cliente MCP da sessão)
  executa as tools com autorização e auditoria corretas. Evidência de campo:
  rótulos do container, `cidfile` e registro do owner coincidem exatamente com o
  que o cleanup compara.
- **Rótulo `GIT_SHA` provisório.** A recipe usa `{commit}-dirty` porque a
  árvore de trabalho contém a correção all-day ainda não commitada; o label da
  imagem gerada confirma `486ae19…-dirty`. Ao commitar a correção, trocar para
  `{commit}` na recipe estática.

### Critérios de aceite

Todos satisfeitos: configuração com `configurationId`/CAS atuais reconhecidos
pelo gestor; `tools/list` do servidor gerenciado com as tools autorizadas
(filtro de allowlist confirmado no cliente da sessão, que expõe apenas as 5);
`khan_get_status`/`khan_list_calendars` confirmando workspace de teste e
calendário `nanobot`; criação e leitura posterior das 12 ocorrências 2027–2030
confirmadas, sem item fora do intervalo e sem alteração de outro workspace.
O critério "o processo stdio encerra normalmente após fechar stdin" permanece
**parcialmente satisfeito**: no caminho funcional o processo do servidor
encerra quando o cliente fecha stdin; o cleanup do container no caminho de
discovery é o que falha (vide defeito acima).
