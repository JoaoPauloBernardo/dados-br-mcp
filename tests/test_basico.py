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
