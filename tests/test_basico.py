import pytest

from dados_br_mcp.catalogo import resolver
from dados_br_mcp.clients import _pontos_sgs, parse_data, to_float


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


def test_pontos_sgs_ordena_por_data():
    # Ordem que o SGS devolve em /ultimos para algumas séries (mais novo primeiro),
    # cruzando a virada de ano para garantir ordenação por data e não por texto.
    bruto = [
        {"data": "02/01/2026", "valor": "13.65"},
        {"data": "31/12/2025", "valor": "13.75"},
        {"data": "30/12/2025", "valor": ""},
    ]
    pontos = _pontos_sgs(bruto)
    assert [p["date"] for p in pontos] == ["30/12/2025", "31/12/2025", "02/01/2026"]
    assert pontos[-1]["val"] == 13.65
    assert pontos[0]["val"] is None
