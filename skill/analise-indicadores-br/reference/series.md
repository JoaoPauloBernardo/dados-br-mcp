# Guia de séries SGS e tabelas SIDRA

Códigos conferidos nas APIs do BCB e do IBGE em 08/11/2026. Séries com apelido podem ser pedidas pelo nome
(`"serie": "ipca"`); as demais, pelo código (`"serie": "1178"`).

## BCB / SGS (tools `ultimos_valores` e `buscar_serie`)

### Juros

| Apelido      | Código | O que mede                                           | Unidade | Frequência |
|--------------|-------:|------------------------------------------------------|---------|------------|
| `selic_meta` | 432    | Meta da Selic definida pelo Copom                    | % a.a.  | diária     |
|              | 1178   | Selic efetiva (over), anualizada base 252            | % a.a.  | diária     |
|              | 4189   | Selic acumulada no mês, anualizada base 252          | % a.a.  | mensal     |
|              | 4390   | Selic acumulada no mês                               | % a.m.  | mensal     |
|              | 11     | Selic efetiva do dia                                 | % a.d.  | diária     |

- **Meta x efetiva:** a meta (432) é a decisão do Copom; a efetiva (1178) é a taxa praticada, normalmente
  um pouco abaixo da meta (ex.: meta 13,75% e efetiva 13,65% em nov/2026). "Selic atual" = meta (432).
- **A série 432 tem datas futuras:** o BCB repete a meta vigente até a próxima reunião do Copom. Use o valor
  com data menor ou igual a hoje.
- **4390 do mês corrente é parcial** (acumula só os dias úteis já decorridos).

### Inflação

| Apelido    | Código | O que mede                         | Unidade  | Frequência |
|------------|-------:|------------------------------------|----------|------------|
| `ipca`     | 433    | IPCA, variação mensal              | % no mês | mensal     |
| `ipca_12m` | 13522  | IPCA acumulado em 12 meses         | %        | mensal     |
|            | 13521  | Meta de inflação (CMN)             | %        | anual      |
| `igpm`     | 189    | IGP-M, variação mensal (FGV)       | % no mês | mensal     |
|            | 190    | IGP-DI, variação mensal (FGV)      | % no mês | mensal     |

- IPCA é o índice oficial da meta de inflação. IGP-M/IGP-DI são índices gerais de preços (pesam preços no
  atacado e commodities) e são usados em contratos, como aluguel.
- A data `01/mm/aaaa` nas séries mensais indica o **mês de referência**, não o dia da divulgação.

### Câmbio

| Apelido | Código | O que mede                        | Unidade  | Frequência |
|---------|-------:|-----------------------------------|----------|------------|
| `dolar` | 1      | Dólar americano, venda            | R$/US$   | diária     |
|         | 10813  | Dólar americano, compra           | R$/US$   | diária     |
|         | 21619  | Euro, venda                       | R$/€     | diária     |

Dias sem pregão (fins de semana, feriados) não aparecem na série.

### Atividade, emprego e contas públicas

| Apelido  | Código | O que mede                                              | Unidade      | Frequência |
|----------|-------:|---------------------------------------------------------|--------------|------------|
| `ibc_br` | 24364  | IBC-Br com ajuste sazonal (prévia mensal do PIB, do BCB) | índice       | mensal     |
|          | 4380   | PIB mensal em valores correntes                         | R$ milhões   | mensal     |
|          | 7326   | PIB, variação real anual                                | %            | anual      |
|          | 24369  | Taxa de desocupação (PNAD Contínua, trimestre móvel)    | %            | mensal     |
|          | 13762  | Dívida bruta do governo geral                           | % do PIB     | mensal     |

- IBC-Br é um **índice**: o nível não tem significado sozinho; compare variações (mês contra mês anterior,
  ou contra o mesmo mês do ano anterior).
- 24369: a data `01/09/2026` representa o trimestre móvel **jul-ago-set 2026**.

## IBGE / SIDRA (tool `tabela_sidra`)

| Tabela | O que é                                         | Variáveis úteis                                              | Níveis       |
|-------:|-------------------------------------------------|--------------------------------------------------------------|--------------|
| 1737   | IPCA, série histórica desde dez/1979            | 63 mensal · 69 no ano · 2265 em 12 meses · 2266 número-índice | `n1/all`     |
| 7060   | IPCA por grupos e itens, desde jan/2020         | 63 mensal · 69 no ano · 2265 em 12 meses · 66 peso            | `n1/all`, `n7/all` (regiões metropolitanas), `n6/all` (municípios) |
| 6381   | Taxa de desocupação, PNAD Contínua trimestral móvel | 4099 taxa de desocupação                                  | `n1/all`     |

- **IPCA não existe por UF.** O recorte regional é por região metropolitana (`n7/all`) ou município (`n6/all`)
  na tabela 7060. Sem filtro de classificação, a 7060 devolve o índice geral.
- **Limitação atual:** tabelas que exigem filtro de classificação (ex.: 5932 PIB trimestral, 8888 produção
  industrial) voltam com `val: null`, porque `tabela_sidra` ainda não aceita esse filtro. Para PIB e emprego,
  use as séries do SGS acima.
- Metadados de qualquer tabela (variáveis, níveis, períodos):
  `https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados`
