# Plano: `/app/.local` gravável na imagem Khan Calendar

## Resultado esperado

A imagem limpa do Percival Khan Calendar inicia como `app` (UID/GID 1000), pode
criar o estado XDG em `/app/.local` e completa o handshake MCP com `/data`
sintético gravável, sem tmpfs especial para `/app/.local`.

## Escopo e passos

1. No estágio runtime do `Dockerfile`, criar `/app/.local` com ownership `app:app`
   antes de `USER app`, mantendo `/data` separado.
2. Estender a verificação Docker da CI para executar como o usuário padrão da
   imagem, criar `share/percival/khan-calendar/khal.conf` sob `/app/.local` e
   confirmar UID/GID 1000 no arquivo.
3. Manter e executar o smoke MCP existente com `/data` montado em tmpfs
   sintético, que verifica `initialize`, `tools/list` e `khan_get_status`.
4. Executar o teste de contrato Docker localmente e, se Docker estiver
   disponível, build e smoke da imagem; revisar o diff final.

## Critérios de aceite

- `USER app` permanece o usuário final (UID/GID 1000).
- `/app/.local` é gravável sem montagem especial nesse caminho.
- O probe cria `khal.conf` e confirma ownership 1000:1000 dentro do container.
- O smoke MCP existente termina `initialize`, `tools/list` e leitura segura com
  workspace sintético em `/data`.

## Riscos e limites

- A regressão usa Docker/BuildKit na etapa de CI; o teste estático local continua
  independente do daemon.
- Nenhum workspace real é usado ou tem permissões alteradas.
