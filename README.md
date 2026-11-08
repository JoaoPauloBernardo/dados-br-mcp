# dados-br-mcp

Servidor [MCP](https://modelcontextprotocol.io) em Python que dá a agentes de IA acesso a dados econômicos
públicos do Brasil: séries do Banco Central (BCB/SGS) e tabelas do IBGE (SIDRA). Modelos de linguagem erram
números como Selic, IPCA e câmbio quando respondem de memória, porque esses valores mudam todo mês. Com este
servidor, o agente busca o dado oficial na fonte, recebe valor, unidade e código da série, e pode citar de onde
o número veio.

<!-- Espaço para um print ou GIF do servidor em uso no Claude Desktop. -->

## O que o servidor expõe

| Tipo     | Nome                     | O que faz                                                                 |
|----------|--------------------------|---------------------------------------------------------------------------|
| Tool     | `listar_series`          | Lista as séries que o servidor conhece por apelido (código, unidade, frequência). |
| Tool     | `ultimos_valores`        | Últimos N valores (1 a 20) de uma série do SGS. Melhor opção para "valor atual". |
| Tool     | `buscar_serie`           | Série do SGS entre duas datas (`dd/mm/aaaa`). Diárias: janela máxima de 10 anos. |
| Tool     | `tabela_sidra`           | Consulta uma tabela do IBGE no SIDRA (Brasil, UF ou região metropolitana), com filtro opcional de classificação. |
| Resource | `catalogo://series-sgs`  | Catálogo de séries em JSON, para a aplicação anexar ao contexto.          |
| Prompt   | `panorama_inflacao`      | Roteiro pronto: IPCA, IPCA 12 meses, Selic e juro real ex-post.           |

Séries com apelido:

| Apelido      | Código SGS | Série                           | Unidade  | Frequência |
|--------------|-----------:|---------------------------------|----------|------------|
| `selic_meta` | 432        | Meta Selic definida pelo Copom  | % a.a.   | diária     |
| `ipca`       | 433        | IPCA - variação mensal          | % no mês | mensal     |
| `ipca_12m`   | 13522      | IPCA - acumulado em 12 meses    | %        | mensal     |
| `igpm`       | 189        | IGP-M - variação mensal         | % no mês | mensal     |
| `dolar`      | 1          | Dólar comercial - venda         | R$/US$   | diária     |
| `ibc_br`     | 24364      | IBC-Br com ajuste sazonal       | índice   | mensal     |

Qualquer outra série do SGS pode ser consultada pelo código numérico (ex.: `"serie": "4390"`).

Formato das respostas (`ultimos_valores` e `buscar_serie`):

```json
{
  "fonte": "BCB/SGS 433",
  "serie": "IPCA - variação mensal",
  "unidade": "% no mês",
  "n_pontos": 3,
  "truncado": false,
  "dados": [{"date": "01/09/2026", "val": 0.82}]
}
```

## Instalação

Requisitos: [uv](https://docs.astral.sh/uv/). O Python certo (definido em `.python-version`) é instalado pelo
próprio `uv` se ainda não existir. Node.js só é necessário para o MCP Inspector.

```powershell
git clone https://github.com/JoaoPauloBernardo/dados-br-mcp.git
cd dados-br-mcp
uv sync
```

## Testes

Testes unitários (lógica pura, sem rede):

```powershell
uv run pytest -v
```

MCP Inspector (interface web para chamar tools, ler resources e testar prompts):

```powershell
npx @modelcontextprotocol/inspector uv run dados-br-mcp
```

Smoke client (cliente MCP mínimo via stdio: `initialize` → `tools/list` → `tools/call`):

```powershell
uv run python scripts/smoke_client.py
```

## Uso no Claude Desktop

1. Descubra o caminho absoluto do `uv`:

   ```powershell
   where.exe uv
   ```

2. Edite `%APPDATA%\Claude\claude_desktop_config.json` (Windows) e adicione o servidor, usando caminhos
   absolutos para o `uv` e para a pasta do projeto:

   ```json
   {
     "mcpServers": {
       "dados-economicos-br": {
         "command": "C:\\Users\\SEU_USUARIO\\.local\\bin\\uv.exe",
         "args": ["--directory", "C:\\caminho\\para\\dados-br-mcp", "run", "dados-br-mcp"]
       }
     }
   }
   ```

3. Feche o Claude Desktop **pela bandeja do sistema** (fechar a janela não encerra o app) e abra de novo.
   Se o servidor não aparecer, veja os logs em `%APPDATA%\Claude\logs`.

Caminho absoluto é necessário porque o Claude Desktop não herda o `PATH` do seu terminal.

## Uso no Claude Code

```powershell
claude mcp add dados-br -- uv --directory C:\caminho\dados-br-mcp run dados-br-mcp
```

## Exemplos de perguntas

- "Qual a Selic atual e o IPCA 12m? Qual o juro real?"
- "Compare o dólar em 2024 e 2025."
- "Como foi o IPCA mês a mês nos últimos 12 meses?"
- "Qual foi o IPCA do último mês em cada região metropolitana?" (via `tabela_sidra`: tabela 7060,
  variável 63, nível `n7/all`; o IPCA não é calculado por UF)
- "Quanto o PIB cresceu no último trimestre?" (via `tabela_sidra`: tabela 5932, variável 6564,
  `classificacao="c11255/90707"`)

## Decisões de design

- **`clients.py` separado de `server.py`**: a lógica de acesso aos dados não depende de MCP, então é testável
  sozinha e reaproveitável (ex.: num DAG do Airflow). `server.py` é uma camada fina por cima.
- **SDK oficial `mcp`**: usa o `MCPServer` (`mcp.server.mcpserver`), nome que o antigo `FastMCP` recebeu no
  SDK 2.x; não usa o pacote de terceiros `fastmcp`.
- **`httpx.AsyncClient` com timeout explícito**: as tools são assíncronas e nenhuma chamada fica pendurada.
- **Apelidos de séries** (`ipca`, `selic_meta`) em vez de exigir que o modelo saiba códigos numéricos.
- **Erros que dizem como corrigir**: erros previstos viram `ToolError`, e a mensagem chega ao modelo, que pode
  tentar de novo (ex.: data em formato errado, série desconhecida). Falhas inesperadas não vazam detalhes.
- **Respostas em envelope** (`fonte`, `unidade`, `n_pontos`, `truncado`, `dados`) e teto de 500 pontos
  por resposta, para não estourar o contexto do modelo.
- **Valores sempre `float`** (ou `null` quando a fonte não tem o dado).
- **Somente leitura** e só APIs públicas.
- **Nada de `print()` no servidor**: no transporte stdio, o stdout é o canal do JSON-RPC. Logs vão para stderr.

## Estrutura

```
src/dados_br_mcp/
├── catalogo.py      # séries conhecidas (apelido → código SGS)
├── clients.py       # chamadas HTTP puras ao SGS e ao SIDRA
└── server.py        # tools, resource e prompt MCP
tests/test_basico.py # testes unitários
scripts/smoke_client.py
```

## Fontes

- Banco Central do Brasil, Sistema Gerenciador de Séries Temporais (SGS):
  <https://www3.bcb.gov.br/sgspub> · API: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`
- IBGE, Sistema IBGE de Recuperação Automática (SIDRA): <https://sidra.ibge.gov.br> · API: <https://apisidra.ibge.gov.br>
