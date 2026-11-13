# Issue: Khan MCP não inicializa quando `/app/.local` não é gravável

- **Status:** aberto; contornado no executor Positronic em 2026-11-13
- **Prioridade sugerida:** P1 — o servidor não completa a inicialização MCP em sua configuração de container suportada
- **Identificada em:** 2026-11-13, inicialização gerenciada pelo Positronic
- **Owner / decisão:** Bill Kopp

## Problema

A imagem executa o processo como usuário não-root `app`, mas não cria um
diretório gravável para o estado local da aplicação em `/app/.local`. No
bootstrap, o servidor tenta criar
`/app/.local/share/percival/khan-calendar/khal.conf` e recebe `Permission
denied`. O processo termina antes de responder ao handshake `initialize` do
MCP.

No runtime afetado, o resultado visível foi `mcp-initialize-failed
(initialize)` e o servidor `khan-calendar` permaneceu `degraded`. O health
HTTP do agente Positronic ainda podia responder, mas seu bootcheck falhava ao
exigir que todos os MCPs habilitados estivessem prontos.

O problema foi reproduzido com a imagem `sha256:ab30f01f3a6780cc9939554048f218fb9835031cc11f7c37e2ae69bc87c7822e`, usuário `app`, rede
`none` e o workspace configurado montado em `/data`. A saída do bootstrap foi:

```text
setup_workspace attempt 1/3 failed: [Errno 13] Permission denied: '/app/.local'
Workspace bootstrap failed: [Errno 13] Permission denied: '/app/.local'
```

Executar o mesmo probe como root permitiu a inicialização, confirmando que a
falha é de permissão do diretório de estado interno, não do workspace `/data`
nem do transporte stdio.

## Causa provável

O estágio runtime do `Dockerfile` cria e transfere `/data` para `app`, mas não
prepara o diretório de estado XDG sob `/app`. Como `HOME=/app` e o processo é
iniciado como `app`, qualquer criação de `~/.local/...` falha: `/app` pertence
ao root e `/app/.local` não existe.

O executor Positronic contornou a falha montando um tmpfs privado e gravável em
`/app/.local`. Isso recuperou o runtime, mas deixa outras formas suportadas de
executar a imagem sujeitas ao mesmo erro.

## Correção proposta

No estágio runtime do `Dockerfile`, criar `/app/.local` e atribuí-lo ao usuário
`app` antes de declarar `USER app`, por exemplo com `install -d -o app -g app
/app/.local`. Manter o workspace `/data` e seus dados persistentes separados
desse estado temporário.

Adicionar uma regressão ao contrato da imagem que execute o entrypoint como
`app`, sem o tmpfs especial do Positronic, com `/data` gravável e isolado. O
teste deve confirmar que o servidor completa `initialize` e que
`/app/.local/share/percival/khan-calendar/khal.conf` pode ser criado com o
ownership esperado.

## Critérios de aceite

- A imagem final continua executando com UID/GID não-root `1000:1000`.
- `/app/.local` existe e é gravável por `app` na imagem limpa.
- Um workspace temporário montado em `/data` permite completar o bootstrap e
  o handshake MCP `initialize`, sem permissões adicionais ou execução como
  root.
- O teste verifica o estado no container, não apenas a configuração textual
  do Dockerfile.
- O smoke existente de versão e `tools/list` continua passando.

## Limites

Não alterar ownership ou permissões do workspace real do operador. A correção
deve ficar na imagem e ser validada em workspace sintético; não exige mudança
no contrato público das tools MCP.
