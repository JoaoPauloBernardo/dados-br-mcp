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
