"""Servidor MCP de dados econômicos brasileiros (BCB/SGS e IBGE/SIDRA)."""
import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

# No SDK mcp 2.x, o antigo FastMCP foi renomeado para MCPServer
# (mesma API de decoradores: @mcp.tool(), @mcp.resource(), @mcp.prompt()).
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
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

mcp = MCPServer("dados-economicos-br")

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


@contextmanager
def _erro_para_o_modelo() -> Iterator[None]:
    """Converte erros previstos em ToolError.

    No mcp 2.x, só a mensagem de um ToolError chega ao modelo; qualquer outra
    exceção vira um genérico "Error executing tool X". Como nossas mensagens
    dizem como corrigir a chamada, elas precisam chegar ao modelo.
    """
    try:
        yield
    except (ValueError, clients.FonteIndisponivel) as e:
        raise ToolError(str(e)) from e


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
    with _erro_para_o_modelo():
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
    with _erro_para_o_modelo():
        codigo, meta = resolver(serie)
        log.info("buscar_serie codigo=%s %s a %s", codigo, data_inicial, data_final)
        pontos = await clients.sgs_periodo(codigo, data_inicial, data_final)
    return _envelope(codigo, meta, pontos)


@mcp.tool()
async def tabela_sidra(
    tabela: Annotated[int, Field(description="Número da tabela no SIDRA, ex.: 1737 (IPCA)")],
    variavel: Annotated[int, Field(description="Código da variável, ex.: 63 (IPCA variação mensal)")],
    periodos: Annotated[str, Field(description="'last N' (ex.: 'last 12'), 'all' ou intervalo 'AAAAMM-AAAAMM'")] = "last 12",
    nivel: Annotated[str, Field(description="Nível territorial: 'n1/all' = Brasil, 'n3/all' = todas as UFs, "
                                            "'n7/all' = regiões metropolitanas")] = "n1/all",
    classificacao: Annotated[str | None, Field(description="Filtro de categoria, obrigatório em tabelas com "
                                                           "classificação, ex.: 'c11255/90707' (PIB na tabela 5932), "
                                                           "'c544/129314' (indústria geral na 8888)")] = None,
) -> dict:
    """Consulta uma tabela do IBGE no SIDRA (inflação, PNAD, PIB, produção
    industrial etc.). Use para dados do IBGE que não estão no SGS ou quando
    precisar de recorte regional. Se os valores vierem null, a tabela
    provavelmente exige o parâmetro 'classificacao'."""
    log.info("tabela_sidra t=%s v=%s p=%s n=%s c=%s", tabela, variavel, periodos, nivel, classificacao)
    with _erro_para_o_modelo():
        linhas = await clients.sidra(tabela, variavel, periodos, nivel, classificacao)
    return {
        "fonte": f"IBGE/SIDRA tabela {tabela}, variável {variavel}"
                 + (f", {classificacao}" if classificacao else ""),
        "n_linhas": len(linhas),
        "truncado": len(linhas) > MAX_PONTOS,
        "dados": linhas[-MAX_PONTOS:],
    }


# ------------------------------------------------------------- RESOURCE

@mcp.resource("catalogo://series-sgs", mime_type="application/json")
def recurso_catalogo() -> str:
    """Catálogo de séries SGS conhecidas pelo servidor (JSON)."""
    return json.dumps(catalogo(), ensure_ascii=False, indent=2)


# --------------------------------------------------------------- PROMPT

@mcp.prompt()
def panorama_inflacao() -> str:
    """Roteiro para montar um panorama atual da inflação e dos juros no Brasil."""
    return (
        "Monte um panorama da inflação brasileira usando as tools do servidor "
        "dados-economicos-br: busque os últimos 12 valores de 'ipca', o último "
        "'ipca_12m' e a 'selic_meta' atual. Calcule o juro real ex-post como "
        "(1 + selic) / (1 + ipca_12m) - 1, com as taxas em decimal "
        "(13,75% = 0,1375). Responda com o número principal "
        "primeiro, uma tabela simples dos valores e a fonte com o código de "
        "cada série."
    )


def main() -> None:
    log.info("Iniciando dados-economicos-br (stdio)")
    mcp.run()  # stdio é o padrão


if __name__ == "__main__":
    main()
