---
name: analise-indicadores-br
description: Busca e interpreta indicadores econômicos oficiais do Brasil (Selic, IPCA, IGP-M, câmbio, IBC-Br, PIB, desemprego, dívida pública) usando o MCP dados-economicos-br (BCB/SGS e IBGE/SIDRA). Use quando o usuário perguntar o valor atual ou histórico de um indicador brasileiro, pedir comparação entre períodos, juro real, inflação acumulada, ou um panorama da economia. Não use para previsões de mercado nem para dados de outros países.
---

# Análise de indicadores econômicos do Brasil

Esta skill dá o **método**; o MCP `dados-economicos-br` dá o **acesso**. Todo número da resposta vem de uma
chamada de tool feita nesta conversa. Nada de memória.

## 1. Escolha a série certa

| Pergunta do usuário                            | Série / tabela                                    |
|------------------------------------------------|---------------------------------------------------|
| "Qual a Selic?" / "juros hoje"                 | `selic_meta` (432)                                |
| Selic praticada no mercado, CDI                | 1178 (Selic efetiva, % a.a.)                      |
| "Qual a inflação?" (sem mais detalhe)          | `ipca_12m` (13522), e cite o último `ipca` mensal |
| Inflação de um mês específico                  | `ipca` (433)                                      |
| Inflação por região / por grupo de produtos    | SIDRA 7060 (`n7/all` = regiões metropolitanas)    |
| Reajuste de aluguel                            | `igpm` (189), acumulado em 12 meses               |
| Dólar / câmbio                                 | `dolar` (1); euro: 21619                          |
| Atividade econômica no mês                     | `ibc_br` (24364)                                  |
| Crescimento do PIB no ano                      | 7326                                              |
| Desemprego                                     | 24369 (ou SIDRA 6381, variável 4099)              |
| Dívida pública                                 | 13762 (% do PIB)                                  |
| Meta de inflação                               | 13521                                             |

Detalhes, unidades e armadilhas de cada série: [reference/series.md](reference/series.md).
Na dúvida, chame `listar_series`.

## 2. Escolha a tool certa

- **Valor atual ou recente** → `ultimos_valores` (n de 1 a 20).
- **Período definido** → `buscar_serie`, datas em `dd/mm/aaaa`. Séries diárias aceitam no máximo 10 anos por
  chamada; se `truncado` vier `true`, divida o período.
- **Dados do IBGE ou recorte regional** → `tabela_sidra`.
- Se uma tool devolver erro, **leia a mensagem**: ela diz como corrigir (formato de data, apelido válido).
  Corrija e tente de novo uma vez. Se a fonte estiver fora do ar, diga isso ao usuário.

## 3. Interprete corretamente

- **Ordene por data antes de ler.** O SGS às vezes devolve os pontos do mais novo para o mais antigo. O valor
  mais recente é o de maior data, não necessariamente o último da lista.
- **`selic_meta` tem datas futuras** (a meta vigente é repetida até o próximo Copom). Use a data ≤ hoje.
- **Mensal x acumulado.** Variação mensal (`% no mês`) não é inflação anual. Para 12 meses, prefira a série
  oficial (`ipca_12m`, ou SIDRA 1737 variável 2265). Se precisar calcular (ex.: IGP-M 12m), **componha**, não
  some: `(1+v1/100)·…·(1+v12/100) − 1`. Use `scripts/acumulado.py`:

  ```
  python scripts/acumulado.py 0.16 0.43 0.56 0.39 0.44 0.83 1.31 0.16 0.38 0.43 0.26 0.24
  python scripts/acumulado.py --json resposta.json   # janela móvel de 12 meses
  ```

- **Juro real ex-post** = `(1 + selic) / (1 + ipca_12m) − 1`, com as taxas em **decimal** (13,75% = 0,1375).
  Ex.: Selic 13,75% e IPCA 12m 4,58% → 1,1375 / 1,0458 − 1 = **8,77% a.a.** Não é a diferença simples
  (13,75 − 4,58 = 9,17).
- **Unidades:** `% a.a.`, `% no mês`, `% a.d.`, `R$/US$`, índice, `% do PIB`. Nunca misture unidades numa conta.
  Índices (IBC-Br) só fazem sentido como variação.
- **Defasagem:** cada indicador tem seu atraso de divulgação. O IPCA sai cerca de 10 dias após o fim do
  mês; o IGP-M, no fim do próprio mês; o IBC-Br, cerca de 2 meses depois; o PIB trimestral, cerca de 2 meses
  após o trimestre. Sempre diga **a que mês ou trimestre o dado se refere**, e não chame de "atual" um dado
  de meses atrás sem avisar.
- **Revisões:** PIB e IBC-Br são revisados depois (o ajuste sazonal é recalculado a cada nova divulgação).
  IPCA não é revisado. Ao comparar com números antigos, avise que a série pode ter mudado.
- **`val: null`** significa que a fonte não tem o dado. Diga isso; não preencha.

## 4. Regras inegociáveis

1. **Nunca invente valores.** Sem dado da tool, não há número na resposta.
2. **Sempre cite a fonte e o código** (ex.: "BCB/SGS 433", "IBGE/SIDRA 1737, variável 2265") e a data de
   referência de cada número.
3. Mostre contas derivadas (juro real, acumulados) com a fórmula e os valores usados.
4. Não faça previsões. Se o usuário pedir, apresente os dados e deixe claro que projeção não é dado oficial.

## 5. Formato da resposta

1. **Número principal primeiro**, com unidade e mês de referência.
2. Tabela simples se houver mais de 2 valores (data, valor, unidade).
3. Uma ou duas frases de interpretação (tendência, comparação com a meta, ressalvas de defasagem).
4. Linha final de fontes: `Fontes: BCB/SGS 432, 13522.`

Exemplo:

> **Juro real ex-post: 8,77% a.a.** (Selic meta de 13,75% a.a. em 08/11/2026; IPCA 12m de 4,58% até set/2026)
>
> | Indicador      | Valor       | Referência |
> |----------------|-------------|------------|
> | Selic meta     | 13,75% a.a. | 08/11/2026 |
> | IPCA 12 meses  | 4,58%       | set/2026   |
>
> Cálculo: 1,1375 / 1,0458 − 1. O IPCA 12m segue acima da meta de 3%.
>
> Fontes: BCB/SGS 432, 13522, 13521.
