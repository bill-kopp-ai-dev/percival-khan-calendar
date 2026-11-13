# Issue: smoke MCP reportou processo sem encerrar após `tools/call`

- **Status:** aberto; falha relatada não reproduzida na imagem candidata atual
- **Prioridade sugerida:** P2 até esclarecer a ocorrência; sem falha funcional observada na reprodução atual
- **Identificada em:** 2026-11-13, smoke stdio da imagem do Khan Calendar
- **Owner / decisão:** Bill Kopp

## Problema observado

Uma execução anterior de `scripts/docker-ci-conformance.py` terminou com:

```text
stdio MCP process did not exit after stdin closed
```

O script só emite essa mensagem depois de enviar `tools/call`, receber uma
resposta JSON-RPC de ID 3 e fechar stdin. Portanto, essa mensagem isolada aponta
para o encerramento do processo, não para timeout ou ausência de resposta de
`khan_get_status`. A ocorrência original não preservou stdout/stderr completos,
o código de saída do container, duração do shutdown ou confirmação do image ID;
não é possível atribuir-lhe uma causa com segurança.

## Investigação do fluxo

Em `scripts/docker-ci-conformance.py`:

1. `read_response(1)` aguarda a resposta de `initialize`.
2. `read_response(2)` aguarda a resposta de `tools/list`.
3. Com `--call-tool`, `read_response(3)` aguarda a resposta da chamada antes do
   fechamento de stdin.
4. Só depois o harness fecha `process.stdin` e aguarda até 15 s pelo processo.
   Se expirar, mata o processo e emite a mensagem observada.

Isso corrige a corrida histórica descrita em `tests/test_protocol_stdio.py`, na
qual stdin era fechado antes de receber a resposta e o SDK cancelava o handler
em andamento. Essa corrida anterior não explica por si só a mensagem atual,
pois o caminho atual já recebeu a resposta da tool antes de chegar ao timeout.

O servidor inicia FastMCP via `boot_app.run(transport="stdio")`; não foi
encontrada lógica de shutdown própria no entrypoint que explique um hang após
EOF. A imagem candidata inspecionada foi
`sha256:d695db5075b774c0b2d8ee904f166d8400239ad6d6419fe15928fc986c072393`, com
label de revisão `486ae19-dirty`. Ela contém MCP SDK `1.30.0`.

O Dockerfile aplica `scripts/patch_mcp_cancellation.py` no ambiente de build e
executa `scripts/check_mcp_cancellation.py` antes de copiar o virtualenv para a
imagem final. O patch torna idempotentes as terminações concorrentes de um
requester (`respond`/`cancel`); a imagem inspecionada contém a guarda
`if self._completed: return`. O mecanismo é relevante para cancelamento e
resposta tardia, mas não há evidência de que tenha causado a ocorrência
original.

## Reprodução e resultado atual

Com a imagem local acima e workspace descartável em tmpfs, executei duas vezes
o smoke equivalente ao step de CI:

```bash
.venv/bin/python scripts/docker-ci-conformance.py \
  --image percival-khan-calendar:local-writable-check \
  --mount type=tmpfs,destination=/data,tmpfs-mode=0777 \
  --env KHAN_WORKSPACE_DIR=/data \
  --expected-tool khan_get_status \
  --expected-uid 1000 \
  --compose-service server \
  --call-tool khan_get_status
```

Ambas as execuções passaram, incluindo o encerramento após fechar stdin:

```text
stdio MCP conformance passed: initialize + tools/list (12 tools) + tools/call khan_get_status
```

O `docker image inspect` confirmou o mesmo ID listado acima. Isso torna a falha
**não reproduzível no candidato atual**; não demonstra o que ocorreu na
execução anterior nem exclui uma falha intermitente.

Também executei `scripts/check_mcp_cancellation.py` diretamente no `.venv` local.
Ele falhou em `assert not self._completed` ao executar `cancel-respond`. Isso é
coerente com o teste exercitar o código upstream sem patch no `.venv`; o
Dockerfile aplica o patch apenas ao virtualenv da imagem durante o build. Esse
resultado não é uma falha do smoke da imagem nem prova de causa para o timeout
de shutdown.

## Impacto

Se reproduzível, o harness reprova a etapa `MCP stdio conformance (offline)` do
CI apesar de uma resposta MCP válida já ter sido recebida; clientes que
encerrem a sessão podem igualmente perceber um processo que persiste após EOF.
Na reprodução atual, `initialize`, `tools/list`, `khan_get_status` e o término
limpo passaram duas vezes na imagem candidata.

## Próxima ação

- Em próxima ocorrência, preservar image ID, linha de comando, tempo até EOF,
  retorno do container e stderr após o timeout; manter o registro de que ID 3
  foi recebido antes do fechamento.
- Se voltar a ocorrer, reproduzir sem `--call-tool` e com `--call-tool` na mesma
  imagem. Isso separa shutdown básico do efeito da chamada/cancelamento.
- Não remover nem ampliar o patch de cancelamento com base apenas no relato
  anterior; a reprodução atual passou e não isolou uma causa.

## Critérios para encerrar

- A falha relatada é explicada por evidência da execução original ou por uma
  reprodução controlada; ou é classificada como não reproduzida após evidência
  adequada e sem ocorrência em CI subsequente.
- O smoke com chamada segura confirma a resposta JSON-RPC antes do EOF e
  encerra o container dentro do timeout em imagem identificada por ID.
- Se houver correção, ela mantém os testes de protocolo stdio e a regressão de
  cancelamento/resposta tardia passando no ambiente correspondente à imagem.
