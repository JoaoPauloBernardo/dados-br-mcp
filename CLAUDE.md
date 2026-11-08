# CLAUDE.md — dados-br-mcp

Este arquivo orienta o Claude Code na construção deste projeto. Leia tudo antes de começar.

## Contexto

Projeto de portfólio do João (estagiário de Data Engineering, estudante de Engenharia de Software no INATEL).
Objetivo: um **MCP server** em Python que expõe dados econômicos públicos do Brasil (BCB/SGS e IBGE/SIDRA)
para agentes de IA e, numa etapa posterior, uma **Claude Skill** que orienta o agente a buscar e interpretar esses dados.

- O MCP dá **acesso** (o agente consegue buscar o dado oficial).
- A Skill dá **método** (o agente sabe qual série buscar, como interpretar e como apresentar).

O João está aprendendo MCP com este projeto. Explique o que cada passo faz e por quê, de forma curta e direta.

## Ambiente

- Windows, terminal PowerShell, VSCode.
- Gerenciador de pacotes: `uv`. Python 3.10+.
- Node.js instalado (usado só para o MCP Inspector).

## Regras de trabalho (obrigatórias)

1. **Um passo por vez.** Execute apenas o passo atual do plano abaixo. Não adiante passos.
2. **Antes de cada commit:** rode os testes que existirem (`uv run pytest -v`), mostre o `git diff --stat` e um resumo
   do que mudou, e **espere o João aprovar** antes de commitar.
3. **Mensagens de commit:** Conventional Commits, em português, exatamente como indicado em cada passo.
4. **Nunca faça `git push`** sem o João pedir explicitamente.
5. **Nunca use `print()` no código do servidor.** No transporte stdio, o stdout é o canal do protocolo JSON-RPC;
   qualquer print corrompe a comunicação. Log só via `logging` em `sys.stderr`.
6. **Valores numéricos das séries (`val`) sempre em `float`** (ou `None` quando a fonte não tem o dado).
7. **Só APIs públicas.** Não copiar nem referenciar código da empresa onde o João trabalha.
8. **Mudanças mínimas e focadas** em cada passo. Não refatore o que não faz parte do passo atual.
9. Ao terminar um passo, diga qual é o próximo e pare.

## Arquitetura

```
dados-br-mcp/
├── CLAUDE.md
├── pyproject.toml
├── uv.lock
├── README.md
├── src/dados_br_mcp/
│   ├── __init__.py
│   ├── catalogo.py      # séries conhecidas (apelido → código SGS)
│   ├── clients.py       # chamadas HTTP puras (sem nada de MCP) — testável e reaproveitável
│   └── server.py        # camada MCP fina: tools, resource, prompt
├── tests/
│   └── test_basico.py
├── scripts/
│   └── smoke_client.py  # cliente MCP mínimo via stdio
└── skill/               # (passo 9, só quando o João pedir)
```

Decisões de design (manter):

- `clients.py` separado de `server.py`: lógica de dados testável sem MCP e reaproveitável (ex.: num DAG do Airflow).
- SDK oficial `mcp` com o FastMCP embutido (`from mcp.server.fastmcp import FastMCP`), **não** o pacote de terceiros `fastmcp`.
- `httpx.AsyncClient` com timeout explícito (nada de `requests` bloqueante dentro de tool async).
- Apelidos de séries (`ipca`, `selic_meta`) em vez de exigir código numérico do modelo.
- Mensagens de erro que dizem **como corrigir** (o modelo lê o erro e tenta de novo).
- Respostas em envelope (`fonte`, `unidade`, `n_pontos`, `truncado`, `dados`) e teto `MAX_PONTOS = 500` para não estourar contexto.
- Servidor somente leitura.

---

## Plano de passos

### Passo 1 — Estrutura inicial

Ações:
- Na pasta atual (que já contém este CLAUDE.md), rodar `uv init --package` (cria pyproject, src/, README, .gitignore e o repositório git, se ainda não existir).
- `uv add "mcp[cli]" httpx` e `uv add --dev pytest`.
- Em `pyproject.toml`, ajustar o entry point:
  ```toml
  [project.scripts]
  dados-br-mcp = "dados_br_mcp.server:main"
  ```
- Deixar `src/dados_br_mcp/__init__.py` apenas com uma docstring (o `uv` gera um `main()` com `print`; remover).
- Criar um `src/dados_br_mcp/server.py` provisório só com `def main() -> None: ...` para o entry point não quebrar.
- Conferir se `.gitignore` cobre `.venv/`, `__pycache__/`, `.pytest_cache/`.
- README provisório de 2 linhas (o completo vem no passo 8).

Critério de pronto: `uv sync` funciona; `uv run python -c "import dados_br_mcp"` funciona.

Commit: `chore: estrutura inicial do projeto com uv`

---

### Passo 2 — Catálogo de séries

Criar `src/dados_br_mcp/catalogo.py` (implementação de referência no Apêndice A).

Avisar o João para **conferir os códigos SGS** no site do SGS antes de commitar.

Critério de pronto: `uv run python -c "from dados_br_mcp.catalogo import resolver; print(resolver('ipca'))"` retorna o código 433.

Commit: `feat: catálogo de séries SGS com resolução por apelido`

---

### Passo 3 — Clients HTTP

Criar `src/dados_br_mcp/clients.py` (Apêndice B).

Pontos a explicar ao João: por que async, por que timeout, por que validar data antes de chamar a API,
regra do SGS para séries diárias (exige `dataInicial`/`dataFinal`, janela máxima de 10 anos).

Critério de pronto: um teste manual rápido busca os últimos 3 valores do IPCA (código 433) e imprime floats.

Commit: `feat: clients assíncronos para SGS/BCB e SIDRA/IBGE`

---

### Passo 4 — Testes unitários

Criar `tests/test_basico.py` (Apêndice C). Só lógica pura, sem rede.

Critério de pronto: `uv run pytest -v` todo verde.

Commit: `test: testes unitários do catálogo e dos helpers`

---

### Passo 5 — Servidor MCP (tools)

Substituir o `server.py` provisório pela parte de tools do Apêndice D:
`listar_series`, `ultimos_valores`, `buscar_serie`, `tabela_sidra`, mais `main()`.

Explicar ao João: o nome da função vira o nome da tool, a docstring vira a descrição, os type hints e
`Annotated[..., Field(...)]` viram o `inputSchema`; exceções viram resultado com `isError: true`.

Testar com o MCP Inspector:
```powershell
npx @modelcontextprotocol/inspector uv run dados-br-mcp
```
Pedir ao João para chamar `ultimos_valores` (serie=ipca, n=3) e testar os erros de propósito (serie=inflacao; data 2024-01-01).

Critério de pronto: as 4 tools aparecem no Inspector, retornam dados e os erros vêm com mensagem amigável.

Commit: `feat: servidor MCP com tools de consulta`

---

### Passo 6 — Resource e prompt

Adicionar ao `server.py` o resource `catalogo://series-sgs` e o prompt `panorama_inflacao` (fim do Apêndice D).

Explicar ao João os três primitivos e quem controla cada um: tools (modelo), resources (aplicação), prompts (usuário).

Critério de pronto: resource e prompt aparecem nas abas correspondentes do Inspector.

Commit: `feat: resource do catálogo e prompt de panorama da inflação`

---

### Passo 7 — Smoke client

Criar `scripts/smoke_client.py` (Apêndice E) e rodar com `uv run python scripts/smoke_client.py`.

Explicar ao João: o script faz o mesmo que o Claude Desktop faz (initialize → tools/list → tools/call).

Critério de pronto: lista as tools, imprime os valores do IPCA e mostra `isError = True` no caso de erro.

Commit: `test: smoke client MCP via stdio`

---

### Passo 8 — README e integração com Claude Desktop

Escrever o README completo, em português, contendo:
- O que é o projeto e por que existe (1 parágrafo).
- Tools, resource e prompt disponíveis (tabela simples).
- Instalação (`uv sync`) e testes (`pytest`, Inspector, smoke client).
- Configuração no Claude Desktop (Windows: `%APPDATA%\Claude\claude_desktop_config.json`), usando o
  **caminho absoluto do uv** (`where.exe uv`) e `--directory` com caminho absoluto:
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
  Lembrar: fechar o Claude Desktop pela bandeja do sistema e reabrir; logs em `%APPDATA%\Claude\logs`.
- Configuração no Claude Code: `claude mcp add dados-br -- uv --directory C:\caminho\dados-br-mcp run dados-br-mcp`.
- Decisões de design (lista curta da seção Arquitetura).
- Exemplos de perguntas: "Qual a Selic atual e o IPCA 12m? Qual o juro real?", "Compare o dólar em 2024 e 2025".
- Espaço para um print/GIF (o João adiciona depois).
- Fontes: BCB/SGS e IBGE/SIDRA.

Sem emojis em excesso, sem marketing. Tom técnico e direto.

Commit: `docs: README com instalação e configuração no Claude Desktop`

Depois deste passo, perguntar ao João se ele quer criar o repositório remoto. Sugestão:
`gh repo create dados-br-mcp --public --source . --push` (só executar com aprovação explícita).

---

### Passo 9 — Skill (NÃO executar até o João pedir)

Pasta `skill/analise-indicadores-br/` com:
- `SKILL.md`: frontmatter `name` e `description` (quando usar a skill) e instruções de como o agente deve
  **buscar e interpretar** os dados usando o MCP `dados-economicos-br`:
  qual série usar para cada tipo de pergunta, variação mensal vs acumulado 12m, juro real ex-post,
  unidades, defasagem e revisões das fontes, nunca inventar valores, sempre citar fonte e código.
- `reference/series.md`: guia de séries SGS/SIDRA mais usadas e o que cada uma mede.
- `scripts/acumulado.py`: cálculo do acumulado em 12 meses a partir de variações mensais.

Commit: `feat(skill): skill de análise de indicadores econômicos`

O conteúdo detalhado da skill será definido com o João quando chegar a hora.

---

## Apêndices — implementações de referência

Use como base. Se alguma API do SDK `mcp` tiver mudado na versão instalada, adapte e explique ao João o que mudou.

### Apêndice A — `src/dados_br_mcp/catalogo.py`

```python
"""Catálogo de séries do SGS que o servidor conhece por apelido."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Serie:
    codigo: int
    nome: str
    unidade: str
    frequencia: str


SERIES_SGS: dict[str, Serie] = {
    "selic_meta": Serie(432, "Meta Selic definida pelo Copom", "% a.a.", "diária"),
    "ipca": Serie(433, "IPCA - variação mensal", "% no mês", "mensal"),
    "ipca_12m": Serie(13522, "IPCA - acumulado em 12 meses", "%", "mensal"),
    "igpm": Serie(189, "IGP-M - variação mensal", "% no mês", "mensal"),
    "dolar": Serie(1, "Dólar comercial - venda", "R$/US$", "diária"),
    "ibc_br": Serie(24364, "IBC-Br com ajuste sazonal", "índice", "mensal"),
}


def catalogo() -> list[dict]:
    return [{"apelido": k, **asdict(s)} for k, s in SERIES_SGS.items()]


def resolver(serie: str) -> tuple[int, Serie | None]:
    """Aceita apelido ('ipca') ou código numérico ('433')."""
    s = serie.strip().lower()
    if s in SERIES_SGS:
        meta = SERIES_SGS[s]
        return meta.codigo, meta
    if s.isdigit():
        codigo = int(s)
        meta = next((m for m in SERIES_SGS.values() if m.codigo == codigo), None)
        return codigo, meta
    apelidos = ", ".join(SERIES_SGS)
    raise ValueError(
        f"Série '{serie}' não reconhecida. Use um apelido ({apelidos}) "
        "ou um código numérico do SGS."
    )
```

### Apêndice B — `src/dados_br_mcp/clients.py`

```python
"""Acesso às APIs públicas do BCB (SGS) e do IBGE (SIDRA)."""
from datetime import date, datetime

import httpx

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
SIDRA_URL = "https://apisidra.ibge.gov.br/values"
TIMEOUT = httpx.Timeout(30.0)
HEADERS = {"User-Agent": "dados-br-mcp/0.1"}


class FonteIndisponivel(Exception):
    """Erro de rede ou HTTP ao consultar uma fonte."""


def to_float(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def parse_data(d: str) -> date:
    try:
        return datetime.strptime(d.strip(), "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(
            f"Data '{d}' inválida. Use o formato dd/mm/aaaa, ex.: 01/01/2024."
        ) from None


async def _get_json(url: str, params: dict | None = None):
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FonteIndisponivel(
                f"{url} respondeu HTTP {e.response.status_code}: "
                f"{e.response.text[:200]}"
            ) from e
        except httpx.RequestError as e:
            raise FonteIndisponivel(f"Falha de rede ao acessar {url}: {e}") from e
        return r.json()


def _pontos_sgs(dados: list[dict]) -> list[dict]:
    return [{"date": x["data"], "val": to_float(x["valor"])} for x in dados]


async def sgs_periodo(codigo: int, data_inicial: str, data_final: str) -> list[dict]:
    di, df = parse_data(data_inicial), parse_data(data_final)
    if di > df:
        raise ValueError("data_inicial é posterior a data_final.")
    params = {
        "formato": "json",
        "dataInicial": di.strftime("%d/%m/%Y"),
        "dataFinal": df.strftime("%d/%m/%Y"),
    }
    return _pontos_sgs(await _get_json(SGS_URL.format(codigo=codigo), params))


async def sgs_ultimos(codigo: int, n: int) -> list[dict]:
    url = SGS_URL.format(codigo=codigo) + f"/ultimos/{n}"
    return _pontos_sgs(await _get_json(url, {"formato": "json"}))


async def sidra(tabela: int, variavel: int, periodos: str, nivel: str) -> list[dict]:
    url = f"{SIDRA_URL}/t/{tabela}/{nivel}/v/{variavel}/p/{periodos}"
    header, *rows = await _get_json(url)
    out = []
    for row in rows:
        # Mantém só os campos de nome (terminam em "N") e o valor: resposta enxuta.
        item = {header[k]: v for k, v in row.items() if k.endswith("N")}
        item["val"] = to_float(row["V"])
        out.append(item)
    return out
```

### Apêndice C — `tests/test_basico.py`

```python
import pytest

from dados_br_mcp.catalogo import resolver
from dados_br_mcp.clients import parse_data, to_float


def test_resolver_apelido():
    codigo, meta = resolver("IPCA")
    assert codigo == 433 and meta is not None


def test_resolver_codigo_fora_do_catalogo():
    codigo, meta = resolver("1234")
    assert codigo == 1234 and meta is None


def test_resolver_invalido():
    with pytest.raises(ValueError, match="não reconhecida"):
        resolver("inflacao")


def test_to_float():
    assert to_float("0,52") == 0.52
    assert to_float("0.52") == 0.52
    assert to_float("...") is None


def test_parse_data_invalida():
    with pytest.raises(ValueError, match="dd/mm/aaaa"):
        parse_data("2024-01-01")
```

### Apêndice D — `src/dados_br_mcp/server.py`

Passo 5 usa tudo até `main()` (sem a seção RESOURCE/PROMPT). Passo 6 adiciona RESOURCE e PROMPT.

```python
"""Servidor MCP de dados econômicos brasileiros (BCB/SGS e IBGE/SIDRA)."""
import json
import logging
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dados_br_mcp import clients
from dados_br_mcp.catalogo import Serie, catalogo, resolver

# No transporte stdio, o stdout É o canal do protocolo.
# Qualquer print() corrompe o JSON-RPC. Log sempre em stderr.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("dados-br-mcp")

mcp = FastMCP("dados-economicos-br")

# Teto de pontos devolvidos ao modelo: cada ponto custa tokens de contexto.
MAX_PONTOS = 500

SerieArg = Annotated[
    str,
    Field(description="Apelido do catálogo (ex.: 'ipca', 'selic_meta', 'dolar') "
                      "ou código numérico do SGS (ex.: '433')"),
]
DataBR = Annotated[str, Field(description="Data no formato dd/mm/aaaa, ex.: 01/01/2024")]


def _envelope(codigo: int, meta: Serie | None, pontos: list[dict]) -> dict:
    return {
        "fonte": f"BCB/SGS {codigo}",
        "serie": meta.nome if meta else "fora do catálogo",
        "unidade": meta.unidade if meta else None,
        "n_pontos": len(pontos),
        "truncado": len(pontos) > MAX_PONTOS,
        "dados": pontos[-MAX_PONTOS:],
    }


# ----------------------------------------------------------------- TOOLS

@mcp.tool()
def listar_series() -> list[dict]:
    """Lista as séries do Banco Central que este servidor conhece por apelido,
    com código SGS, unidade e frequência. Use quando não souber o apelido
    ou o código certo de um indicador."""
    return catalogo()


@mcp.tool()
async def ultimos_valores(
    serie: SerieArg,
    n: Annotated[int, Field(ge=1, le=20, description="Quantidade de valores mais recentes (1 a 20)")] = 12,
) -> dict:
    """Retorna os N valores mais recentes de uma série do SGS/BCB.
    É a melhor opção para perguntas sobre o valor atual ou recente de um
    indicador (ex.: 'qual a Selic hoje?', 'IPCA dos últimos meses')."""
    codigo, meta = resolver(serie)
    log.info("ultimos_valores codigo=%s n=%s", codigo, n)
    pontos = await clients.sgs_ultimos(codigo, n)
    return _envelope(codigo, meta, pontos)


@mcp.tool()
async def buscar_serie(serie: SerieArg, data_inicial: DataBR, data_final: DataBR) -> dict:
    """Retorna uma série do SGS/BCB entre duas datas.
    Para séries diárias (ex.: dolar, selic_meta), o intervalo máximo é de
    10 anos. Se houver mais de 500 pontos, só os 500 mais recentes são
    retornados e o campo 'truncado' vem true; nesse caso, reduza o período."""
    codigo, meta = resolver(serie)
    log.info("buscar_serie codigo=%s %s a %s", codigo, data_inicial, data_final)
    pontos = await clients.sgs_periodo(codigo, data_inicial, data_final)
    return _envelope(codigo, meta, pontos)


@mcp.tool()
async def tabela_sidra(
    tabela: Annotated[int, Field(description="Número da tabela no SIDRA, ex.: 1737 (IPCA)")],
    variavel: Annotated[int, Field(description="Código da variável, ex.: 63 (IPCA variação mensal)")],
    periodos: Annotated[str, Field(description="'last N' (ex.: 'last 12'), 'all' ou intervalo 'AAAAMM-AAAAMM'")] = "last 12",
    nivel: Annotated[str, Field(description="Nível territorial: 'n1/all' = Brasil, 'n3/all' = todas as UFs")] = "n1/all",
) -> dict:
    """Consulta uma tabela do IBGE no SIDRA (inflação, PNAD, PIB, produção
    industrial etc.). Use para dados do IBGE que não estão no SGS ou quando
    precisar de recorte por UF."""
    log.info("tabela_sidra t=%s v=%s p=%s n=%s", tabela, variavel, periodos, nivel)
    linhas = await clients.sidra(tabela, variavel, periodos, nivel)
    return {
        "fonte": f"IBGE/SIDRA tabela {tabela}, variável {variavel}",
        "n_linhas": len(linhas),
        "truncado": len(linhas) > MAX_PONTOS,
        "dados": linhas[-MAX_PONTOS:],
    }


# ------------------------------------------------- RESOURCE (passo 6)

@mcp.resource("catalogo://series-sgs")
def recurso_catalogo() -> str:
    """Catálogo de séries SGS conhecidas pelo servidor (JSON)."""
    return json.dumps(catalogo(), ensure_ascii=False, indent=2)


# --------------------------------------------------- PROMPT (passo 6)

@mcp.prompt()
def panorama_inflacao() -> str:
    """Roteiro para montar um panorama atual da inflação e dos juros no Brasil."""
    return (
        "Monte um panorama da inflação brasileira usando as tools do servidor "
        "dados-economicos-br: busque os últimos 12 valores de 'ipca', o último "
        "'ipca_12m' e a 'selic_meta' atual. Calcule o juro real ex-post como "
        "(1 + selic) / (1 + ipca_12m) - 1. Responda com o número principal "
        "primeiro, uma tabela simples dos valores e a fonte com o código de "
        "cada série."
    )


def main() -> None:
    log.info("Iniciando dados-economicos-br (stdio)")
    mcp.run()  # stdio é o padrão


if __name__ == "__main__":
    main()
```

### Apêndice E — `scripts/smoke_client.py`

```python
"""Cliente MCP mínimo: sobe o servidor via stdio, lista e chama tools."""
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PARAMS = StdioServerParameters(command="uv", args=["run", "dados-br-mcp"])


async def main() -> None:
    async with stdio_client(PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools disponíveis:")
            for t in tools.tools:
                print(f"  - {t.name}")

            ok = await session.call_tool("ultimos_valores", {"serie": "ipca", "n": 3})
            print("\nultimos_valores(ipca, 3):", ok.content[0].text)

            erro = await session.call_tool("ultimos_valores", {"serie": "inflacao"})
            print("\nerro esperado -> isError =", erro.isError)
            print(erro.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
```

(`print` aqui é permitido: este script é o **cliente**, não o servidor.)
