"""Acesso às APIs públicas do BCB (SGS) e do IBGE (SIDRA)."""
import re
from datetime import date, datetime

import httpx

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
SIDRA_URL = "https://apisidra.ibge.gov.br/values"
TIMEOUT = httpx.Timeout(30.0)
HEADERS = {"User-Agent": "dados-br-mcp/0.1"}


# Filtro de classificação do SIDRA: "c<id>/<categorias>", ex.: "c11255/90707"
# ou "c544/129314,129315". Vários filtros separados por "/".
_CLASSIFICACAO = re.compile(r"c\d+/(all|allxt|\d+(,\d+)*)(/c\d+/(all|allxt|\d+(,\d+)*))*")


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
    # O SGS nem sempre devolve em ordem cronológica (ex.: /ultimos da série 1178
    # vem do mais novo para o mais antigo). Ordenamos para o último ponto ser
    # sempre o mais recente; o corte de MAX_PONTOS no servidor depende disso.
    pontos = [{"date": x["data"], "val": to_float(x["valor"])} for x in dados]
    return sorted(pontos, key=lambda p: parse_data(p["date"]))


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


def validar_classificacao(classificacao: str) -> str:
    c = classificacao.strip().lower()
    if not _CLASSIFICACAO.fullmatch(c):
        raise ValueError(
            f"Classificação '{classificacao}' inválida. Use 'c<id>/<categoria>', "
            "ex.: 'c11255/90707' (PIB a preços de mercado na tabela 5932). "
            "Os ids estão em https://servicodados.ibge.gov.br/api/v3/agregados/<tabela>/metadados"
        )
    return c


async def sidra(
    tabela: int, variavel: int, periodos: str, nivel: str, classificacao: str | None = None
) -> list[dict]:
    url = f"{SIDRA_URL}/t/{tabela}/{nivel}/v/{variavel}/p/{periodos}"
    if classificacao:
        url += "/" + validar_classificacao(classificacao)
    header, *rows = await _get_json(url)
    out = []
    for row in rows:
        # Mantém só os campos de nome (terminam em "N") e o valor: resposta enxuta.
        item = {header[k]: v for k, v in row.items() if k.endswith("N")}
        item["val"] = to_float(row["V"])
        out.append(item)
    return out
