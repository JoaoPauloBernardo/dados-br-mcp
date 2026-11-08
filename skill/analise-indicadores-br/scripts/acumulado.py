"""Acumulado de variações mensais (ex.: IPCA em 12 meses).

As variações se acumulam por composição, não por soma:

    acumulado = (1 + v1/100) * (1 + v2/100) * ... * (1 + vn/100) - 1

Uso:
    # Acumulado de uma lista de variações mensais em %:
    python acumulado.py 0.16 0.43 0.56 0.39 0.44 0.83 1.31 0.16 0.38 0.43 0.26 0.24

    # Acumulado em 12 meses, mês a mês, a partir da resposta JSON de
    # ultimos_valores/buscar_serie (precisa de pelo menos 12 meses):
    python acumulado.py --json resposta.json
    python acumulado.py --json - < resposta.json

Só biblioteca padrão. Sem rede.
"""
import argparse
import json
import sys
from datetime import datetime


def acumulado(variacoes: list[float]) -> float:
    """Acumula variações percentuais por composição. Retorna em %."""
    if not variacoes:
        raise ValueError("Nenhuma variação informada.")
    if any(v is None for v in variacoes):
        raise ValueError("Há meses sem valor (None): não dá para acumular sem inventar dado.")
    fator = 1.0
    for v in variacoes:
        fator *= 1 + v / 100
    return (fator - 1) * 100


def _data(d: str) -> datetime:
    return datetime.strptime(d, "%d/%m/%Y")


def acumulado_janela(pontos: list[dict], meses: int = 12) -> list[dict]:
    """Acumulado em janela móvel de `meses` para pontos {"date": "dd/mm/aaaa", "val": float}.

    Ordena por data antes de calcular (o SGS nem sempre devolve em ordem).
    """
    ordenados = sorted(pontos, key=lambda p: _data(p["date"]))
    if len(ordenados) < meses:
        raise ValueError(f"São necessários pelo menos {meses} meses; recebi {len(ordenados)}.")
    return [
        {
            "date": ordenados[i]["date"],
            "val": round(acumulado([p["val"] for p in ordenados[i - meses + 1 : i + 1]]), 2),
        }
        for i in range(meses - 1, len(ordenados))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Acumulado de variações mensais (%).")
    parser.add_argument("variacoes", nargs="*", type=float, help="variações mensais em %%")
    parser.add_argument("--json", metavar="ARQUIVO", help="resposta JSON do servidor ('-' = stdin)")
    parser.add_argument("--meses", type=int, default=12, help="tamanho da janela (padrão: 12)")
    args = parser.parse_args()

    if args.json:
        fonte = sys.stdin if args.json == "-" else open(args.json, encoding="utf-8")
        with fonte:
            dados = json.load(fonte)
        pontos = dados["dados"] if isinstance(dados, dict) else dados
        for p in acumulado_janela(pontos, args.meses):
            print(f"{p['date']}  {p['val']:.2f}%")
    elif args.variacoes:
        print(f"{acumulado(args.variacoes):.2f}%")
    else:
        parser.error("informe variações ou --json")


if __name__ == "__main__":
    main()
